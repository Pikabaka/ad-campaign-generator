"""Async generation pipeline with SSE-friendly progress events.

Stages:
  1. slogan + theme + voiceover script   (GPT-4o-mini, ~3-5s)
  2. parallel: poster (gpt-image-1), TTS (tts-1), BGM (fal.ai music)
  3. video (Kling, ~2-5min)
  4. ffmpeg compose video + tts + bgm
  5. social-size variants (PIL)
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path

import fal_client
import requests
from openai import AsyncOpenAI

from presets import get_preset
from social_resize import generate_social_sizes


COSTS = {
    "slogan": 0.001,
    "poster": 0.084,   # 2x gpt-image-1 1024x1536 medium (display + clean for i2v)
    "tts": 0.015,
    "bgm": 0.020,
    "video": 0.350,
}


def _load_config():
    cfg_path = Path(__file__).parent / "api_config.json"
    if not cfg_path.exists():
        raise FileNotFoundError("api_config.json missing")
    with open(cfg_path) as f:
        return json.load(f)


async def _emit(state, event_type, data):
    """Append an event to the job state's event log (polled by client)."""
    state["events"].append({"event": event_type, "data": data})
    state["updated_at"] = time.time()


async def _generate_slogan_and_theme(client: AsyncOpenAI, product_info, preset):
    """Step 1: GPT-4o-mini produces slogan, theme, voiceover script."""
    style_block = ""
    if preset:
        style_block = f"""
STYLE PRESET: {preset['name']}
- Visual Style: {preset['visual_style']}
- Color Palette: {preset['color_palette']}
- Tone: {preset['tone']}
"""

    prompt = f"""You are a creative advertising director. Build an ad campaign.

COMPANY: {product_info['company_name']}
- {product_info['company_description']}

PRODUCT: {product_info['product_name']}
- {product_info['product_description']}

TARGET AUDIENCE: {product_info['target_audience']}

KEY SELLING POINTS:
{chr(10).join('  - ' + p for p in product_info['selling_points'])}

BRAND COLORS: {product_info['brand_colors']}
CALL TO ACTION: {product_info['call_to_action']}
{product_info.get('additional_info') or ''}
{style_block}

Respond with ONLY this JSON (no markdown):
{{
  "slogan": "catchy slogan, max 10 words",
  "theme": "overall visual + emotional theme, 1-2 sentences",
  "tone": "tone/mood",
  "color_palette": "suggested palette",
  "visual_style": "describe poster + video visuals",
  "voiceover_script": "2-3 short sentences for a 10-second video voiceover, ends with the CTA"
}}"""

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a creative advertising director. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.85,
        max_tokens=600,
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)


async def _generate_poster(client: AsyncOpenAI, product_info, theme, preset, out_path: Path,
                           include_text: bool = True):
    """Generate a poster with gpt-image-1, save PNG to out_path.

    `include_text=True`  → standard poster with slogan typography (display version).
    `include_text=False` → same scene WITHOUT any text — used as Kling i2v
                            keyframe so video models don't try to animate text
                            into garbled gibberish.
    """
    style_str = (preset['visual_style'] if preset else theme['visual_style'])
    palette = (preset['color_palette'] if preset else theme['color_palette'])
    tone = (preset['tone'] if preset else theme['tone'])

    if include_text:
        text_block = f"""Slogan to feature prominently: "{theme['slogan']}"
Include the product name as bold typography."""
        text_constraint = "Eye-catching, premium magazine quality, suitable for a billboard or print campaign. No watermarks, no logos that aren't the product brand."
    else:
        text_block = "No slogans, no headlines, no captions."
        text_constraint = (
            "ABSOLUTELY NO TEXT, NO TYPOGRAPHY, NO WORDS, NO LETTERS, NO NUMBERS, "
            "NO WRITTEN ELEMENTS OF ANY KIND. The image must be purely visual — "
            "atmosphere, subject, and composition only. Where the slogan would "
            "have gone, leave atmospheric negative space (light, gradient, or "
            "scene continuation). This image will be used as the first frame of "
            "a video, so it must read as a pure scene without writing."
        )

    image_prompt = f"""Professional advertising poster for {product_info['product_name']} by {product_info['company_name']}.

{text_block}

Visual style: {style_str}
Color palette: {palette}
Tone: {tone}
Theme: {theme['theme']}

The poster must look like a real high-end print advertisement. Vertical 2:3 composition. {text_constraint}"""

    # Try gpt-image-1 first; fall back to dall-e-3, then dall-e-2.
    last_err = None
    for model, size, kwargs in [
        ("gpt-image-1", "1024x1536", {"quality": "medium"}),
        ("dall-e-3", "1024x1792", {"quality": "standard"}),
        ("dall-e-2", "1024x1024", {}),
    ]:
        try:
            resp = await client.images.generate(
                model=model, prompt=image_prompt, size=size, n=1, **kwargs
            )
            data = resp.data[0]
            if getattr(data, "b64_json", None):
                out_path.write_bytes(base64.b64decode(data.b64_json))
            else:
                # URL fallback (dall-e-3, dall-e-2)
                r = requests.get(data.url, timeout=60)
                r.raise_for_status()
                out_path.write_bytes(r.content)
            return model
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All image models failed: {last_err}")


async def _generate_tts(client: AsyncOpenAI, voiceover_script, voice, out_path: Path, instructions: str | None = None):
    """Step 2b: OpenAI TTS — save MP3.

    Uses gpt-4o-mini-tts which supports `instructions` for delivery style
    (e.g. "speak like a sports broadcaster"). Falls back to tts-1 if the
    newer model isn't available on the account.
    """
    try:
        kwargs = {
            "model": "gpt-4o-mini-tts",
            "voice": voice,
            "input": voiceover_script,
        }
        if instructions:
            kwargs["instructions"] = instructions
        resp = await client.audio.speech.create(**kwargs)
    except Exception as e:
        print(f"[TTS] gpt-4o-mini-tts failed ({e}); falling back to tts-1", file=sys.stderr)
        resp = await client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=voiceover_script,
        )
    out_path.write_bytes(resp.content)


async def _generate_bgm(music_genre, out_path: Path):
    """Step 2c: fal.ai music model. Save MP3."""
    def _sync():
        result = fal_client.submit(
            "cassetteai/music-generator",
            arguments={"prompt": music_genre, "duration": 15},
        )
        return result.get()

    try:
        resp = await asyncio.to_thread(_sync)
    except Exception as primary_err:
        print(f"[BGM] cassetteai failed: {primary_err}", file=sys.stderr)
        # Fallback to stable-audio
        def _stable():
            result = fal_client.submit(
                "fal-ai/stable-audio",
                arguments={"prompt": music_genre, "seconds_total": 15},
            )
            return result.get()
        try:
            resp = await asyncio.to_thread(_stable)
        except Exception as fallback_err:
            print(f"[BGM] stable-audio also failed: {fallback_err}", file=sys.stderr)
            raise RuntimeError(f"All BGM providers failed. cassetteai: {primary_err}; stable-audio: {fallback_err}")

    audio_url = None
    if isinstance(resp, dict):
        if "audio_file" in resp and isinstance(resp["audio_file"], dict):
            audio_url = resp["audio_file"].get("url")
        elif "audio" in resp and isinstance(resp["audio"], dict):
            audio_url = resp["audio"].get("url")
        elif "audio_url" in resp:
            audio_url = resp["audio_url"]

    if not audio_url:
        raise RuntimeError(f"No audio URL in BGM response: {resp}")

    r = await asyncio.to_thread(requests.get, audio_url, timeout=120)
    r.raise_for_status()
    out_path.write_bytes(r.content)


VIDEO_TIMEOUT_SEC = 8 * 60  # 8 minutes hard cap


async def _generate_video(product_info, theme, preset, out_path: Path, poster_path: Path | None = None):
    """Step 3: Kling video via fal.ai.

    Uses image-to-video (i2v) with the poster as the keyframe so the video shows
    the EXACT same product as the poster. Falls back to text-to-video if i2v
    fails or no poster is available.
    """
    style_str = (preset['visual_style'] if preset else theme['visual_style'])

    base_prompt = f"""A 10-second cinematic commercial showcasing {product_info['product_name']} — a {product_info['product_description']}.

Visual style: {style_str}
Mood/theme: {theme['theme']}
Tone: {theme['tone']}

CRITICAL CONSTRAINTS — follow strictly:
- DO NOT render any text, words, captions, slogans, taglines, watermarks, or written letters of any kind. Video models cannot render legible text and any attempt produces gibberish.
- DO NOT include any brand logos, brand names, or trademarks (the product itself is the only brand element). No Apple logos, no swooshes, no recognizable corporate marks.
- If people appear, show diverse subjects across age, gender, ethnicity, and body type. Avoid stereotypical imagery (e.g. don't default to muscular athletes, generic supermodels, etc.).
- Focus on atmosphere, light, motion, and the product itself — not on text reveals.

Camera direction: smooth cinematic motion (slow push-in, gentle dolly, or elegant arc). Premium production value, color-graded like a high-end commercial."""

    def _t2v():
        handle = fal_client.submit(
            "fal-ai/kling-video/v1/standard/text-to-video",
            arguments={"prompt": base_prompt, "duration": 10},
        )
        rid = getattr(handle, "request_id", None)
        if rid:
            print(f"[VIDEO/t2v] fal.ai request_id={rid}", file=sys.stderr)
        return handle.get()

    resp = None

    # Try image-to-video first using the poster as a keyframe.
    if poster_path and Path(poster_path).exists():
        i2v_prompt = (
            base_prompt
            + "\n\nANIMATE THIS IMAGE into a 10-second commercial. "
            "The product must look IDENTICAL to the input image — do not redesign, "
            "restyle, or replace it. Keep the product's exact shape, color, and "
            "composition. Add subtle camera motion (slow push-in or gentle dolly), "
            "soft environmental motion (light shifts, particles, gentle focus pulls), "
            "and natural ambient movement. The first frame should match the input image."
        )

        def _i2v():
            uploaded_url = fal_client.upload_file(str(poster_path))
            print(f"[VIDEO/i2v] uploaded poster: {uploaded_url}", file=sys.stderr)
            handle = fal_client.submit(
                "fal-ai/kling-video/v1/standard/image-to-video",
                arguments={
                    "prompt": i2v_prompt,
                    "image_url": uploaded_url,
                    "duration": "10",
                },
            )
            rid = getattr(handle, "request_id", None)
            if rid:
                print(f"[VIDEO/i2v] fal.ai request_id={rid}", file=sys.stderr)
            return handle.get()

        try:
            resp = await asyncio.wait_for(asyncio.to_thread(_i2v), timeout=VIDEO_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            print(f"[VIDEO/i2v] timed out after {VIDEO_TIMEOUT_SEC}s; falling back to t2v", file=sys.stderr)
            resp = None
        except Exception as e:
            print(f"[VIDEO/i2v] failed ({e}); falling back to t2v", file=sys.stderr)
            resp = None

    # Fallback: text-to-video
    if resp is None:
        try:
            resp = await asyncio.wait_for(asyncio.to_thread(_t2v), timeout=VIDEO_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            raise RuntimeError(f"Kling video generation timed out after {VIDEO_TIMEOUT_SEC}s.")

    video_url = None
    if isinstance(resp, dict):
        if "video" in resp and isinstance(resp["video"], dict):
            video_url = resp["video"].get("url")
        elif "video_url" in resp:
            video_url = resp["video_url"]

    if not video_url:
        raise RuntimeError(f"No video URL in response: {resp}")

    r = await asyncio.to_thread(requests.get, video_url, timeout=300)
    r.raise_for_status()
    out_path.write_bytes(r.content)


def _ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def _compose_video(video_in: Path, tts_in: Path, bgm_in: Path, video_out: Path):
    """Mix Kling video (silent) + TTS (loud) + BGM (quiet) into final mp4."""
    if not _ffmpeg_available():
        # No ffmpeg — copy raw kling video as final
        shutil.copy(video_in, video_out)
        return False

    inputs = ["-i", str(video_in)]
    filters = []
    audio_idx = 1

    if tts_in and tts_in.exists():
        inputs += ["-i", str(tts_in)]
        filters.append(f"[{audio_idx}:a]volume=1.5[a_tts]")
        tts_label = "[a_tts]"
        audio_idx += 1
    else:
        tts_label = None

    if bgm_in and bgm_in.exists():
        inputs += ["-i", str(bgm_in)]
        filters.append(f"[{audio_idx}:a]volume=0.25,aloop=loop=-1:size=2e9[a_bgm]")
        bgm_label = "[a_bgm]"
        audio_idx += 1
    else:
        bgm_label = None

    if tts_label and bgm_label:
        filters.append(f"{tts_label}{bgm_label}amix=inputs=2:duration=first:dropout_transition=0[aout]")
        amap = "[aout]"
    elif tts_label:
        amap = tts_label
    elif bgm_label:
        amap = bgm_label
    else:
        amap = None

    cmd = ["ffmpeg", "-y"] + inputs
    if amap:
        cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", amap]
    else:
        cmd += ["-map", "0:v"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-shortest", str(video_out)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return True
    except Exception as e:
        # Fallback: use raw kling
        shutil.copy(video_in, video_out)
        return False


async def run_pipeline(product_info, preset_id, state: dict, output_root: Path):
    """Main pipeline. Appends events to state['events']. Returns campaign_dir on success.

    `state` is a dict shared with the HTTP layer:
      { "status": "running"|"done"|"error", "events": [], "updated_at": float, ... }
    """
    config = _load_config()
    os.environ["FAL_KEY"] = config["fal_api_key"]
    client = AsyncOpenAI(api_key=config["openai_api_key"])
    preset = get_preset(preset_id) if preset_id else None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    campaign_dir = output_root / f"campaign_{timestamp}"
    campaign_dir.mkdir(parents=True, exist_ok=True)

    cumulative_cost = 0.0
    started = time.time()

    try:
        # === Step 1: slogan + theme ===
        await _emit(state, "step", {"id": "slogan", "status": "running", "label": "Crafting slogan & theme"})
        t0 = time.time()
        theme = await _generate_slogan_and_theme(client, product_info, preset)
        cumulative_cost += COSTS["slogan"]
        await _emit(state, "step", {
            "id": "slogan", "status": "done",
            "elapsed": round(time.time() - t0, 1),
            "cost": COSTS["slogan"], "cumulative_cost": round(cumulative_cost, 3),
            "result": theme,
        })

        # === Step 2: parallel — poster (display) + poster (clean for video) + TTS + BGM ===
        poster_path = campaign_dir / "poster.png"
        poster_clean_path = campaign_dir / "poster_clean.png"  # text-free version for Kling i2v
        tts_path = campaign_dir / "voiceover.mp3"
        bgm_path = campaign_dir / "bgm.mp3"

        await _emit(state, "step", {"id": "poster", "status": "running", "label": "Designing poster (gpt-image-1)"})
        await _emit(state, "step", {"id": "tts", "status": "running", "label": "Synthesizing voiceover"})
        await _emit(state, "step", {"id": "bgm", "status": "running", "label": "Composing BGM"})

        voice = (preset['voice'] if preset else "nova")
        music_genre = (preset['music_genre'] if preset else "uplifting cinematic commercial music")

        async def _poster_task():
            t = time.time()
            # Generate both versions in parallel: display (with text) + clean (for video keyframe)
            display_t = asyncio.create_task(
                _generate_poster(client, product_info, theme, preset, poster_path, include_text=True)
            )
            clean_t = asyncio.create_task(
                _generate_poster(client, product_info, theme, preset, poster_clean_path, include_text=False)
            )
            try:
                model_used, _ = await asyncio.gather(display_t, clean_t)
            except Exception as e:
                # If clean version fails, that's OK — i2v will fall back to t2v.
                # If display fails, this whole step fails.
                if display_t.done() and not display_t.exception():
                    model_used = display_t.result()
                    print(f"[POSTER] clean version failed but display succeeded: {e}", file=sys.stderr)
                else:
                    raise
            return ("poster", model_used, time.time() - t)

        voice_instructions = (preset.get('voice_instructions') if preset else None)

        async def _tts_task():
            t = time.time()
            await _generate_tts(client, theme["voiceover_script"], voice, tts_path, voice_instructions)
            return ("tts", voice, time.time() - t)

        async def _bgm_task():
            t = time.time()
            await _generate_bgm(music_genre, bgm_path)
            return ("bgm", "cassetteai", time.time() - t)

        # Run in parallel; emit completion as each finishes
        tasks = {
            asyncio.create_task(_poster_task()): "poster",
            asyncio.create_task(_tts_task()): "tts",
            asyncio.create_task(_bgm_task()): "bgm",
        }
        for fut in asyncio.as_completed(list(tasks.keys())):
            try:
                kind, info, elapsed = await fut
                cumulative_cost += COSTS[kind]
                payload = {
                    "id": kind, "status": "done",
                    "elapsed": round(elapsed, 1),
                    "cost": COSTS[kind], "cumulative_cost": round(cumulative_cost, 3),
                    "info": info,
                }
                if kind == "poster":
                    payload["url"] = f"/outputs/{campaign_dir.name}/poster.png"
                elif kind == "tts":
                    payload["url"] = f"/outputs/{campaign_dir.name}/voiceover.mp3"
                elif kind == "bgm":
                    payload["url"] = f"/outputs/{campaign_dir.name}/bgm.mp3"
                await _emit(state, "step", payload)
            except Exception as e:
                # Print traceback to terminal so we can debug
                print(f"\n[PIPELINE ERROR] {type(e).__name__}: {e}", file=sys.stderr)
                traceback.print_exc()
                # Find which task this was
                for task, kind in tasks.items():
                    if task.done() and task.exception() is e:
                        await _emit(state, "step", {"id": kind, "status": "error", "error": f"{type(e).__name__}: {e}"})
                        break

        # === Step 2.5: social media variants (fast, do immediately after poster) ===
        if poster_path.exists():
            try:
                sizes = generate_social_sizes(poster_path, campaign_dir)
                await _emit(state, "step", {
                    "id": "social", "status": "done",
                    "label": "Social variants",
                    "sizes": {k: f"/outputs/{campaign_dir.name}/{Path(v).name}" for k, v in sizes.items()},
                })
            except Exception as e:
                await _emit(state, "step", {"id": "social", "status": "error", "error": str(e)})

        # === Step 3: video ===
        await _emit(state, "step", {"id": "video", "status": "running", "label": "Filming 10s video (Kling) — slowest step, ~2-5min"})
        t0 = time.time()
        video_raw = campaign_dir / "video_raw.mp4"
        video_ok = False
        try:
            # Prefer clean (text-free) poster for i2v keyframe to avoid garbled
            # text in the video. Fall back to the display poster if clean failed.
            i2v_keyframe = poster_clean_path if poster_clean_path.exists() else poster_path
            await _generate_video(product_info, theme, preset, video_raw, poster_path=i2v_keyframe)
            cumulative_cost += COSTS["video"]
            video_ok = True
            await _emit(state, "step", {
                "id": "video", "status": "done",
                "elapsed": round(time.time() - t0, 1),
                "cost": COSTS["video"], "cumulative_cost": round(cumulative_cost, 3),
            })
        except Exception as e:
            print(f"\n[VIDEO ERROR] {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc()
            await _emit(state, "step", {
                "id": "video", "status": "error",
                "elapsed": round(time.time() - t0, 1),
                "error": f"{type(e).__name__}: {e}",
            })

        # === Step 4: compose ===
        if video_ok:
            await _emit(state, "step", {"id": "compose", "status": "running", "label": "Mixing audio + video"})
            t0 = time.time()
            final_video = campaign_dir / "ad_video.mp4"
            composed = await asyncio.to_thread(_compose_video, video_raw, tts_path, bgm_path, final_video)
            await _emit(state, "step", {
                "id": "compose", "status": "done",
                "elapsed": round(time.time() - t0, 1),
                "cost": 0, "cumulative_cost": round(cumulative_cost, 3),
                "ffmpeg_used": composed,
                "url": f"/outputs/{campaign_dir.name}/ad_video.mp4",
            })
        else:
            await _emit(state, "step", {
                "id": "compose", "status": "error",
                "error": "Skipped — no video to mix",
            })

        # === Save summary JSON ===
        summary = {
            "timestamp": timestamp,
            "product_info": product_info,
            "preset_id": preset_id,
            "campaign_theme": theme,
            "total_cost": round(cumulative_cost, 3),
            "total_elapsed": round(time.time() - started, 1),
            "video_generated": video_ok,
            "files": {
                "poster": "poster.png",
                "voiceover": "voiceover.mp3",
                "bgm": "bgm.mp3",
                "video": "ad_video.mp4" if video_ok else None,
            },
        }
        with open(campaign_dir / "campaign_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        with open(campaign_dir / "slogan_theme.txt", "w") as f:
            f.write(f"=== AD CAMPAIGN: {product_info['product_name']} ===\n\n")
            f.write(f"SLOGAN: {theme['slogan']}\n\n")
            f.write(f"THEME: {theme['theme']}\n\n")
            f.write(f"TONALITY: {theme['tone']}\n\n")
            f.write(f"VOICEOVER: {theme['voiceover_script']}\n\n")
            f.write(f"COLOR PALETTE: {theme['color_palette']}\n\n")
            f.write(f"VISUAL STYLE: {theme['visual_style']}\n")

        await _emit(state, "complete", {
            "campaign_dir": campaign_dir.name,
            "total_cost": round(cumulative_cost, 3),
            "total_elapsed": round(time.time() - started, 1),
            "summary": summary,
        })
        return campaign_dir

    except Exception as e:
        await _emit(state, "error", {"message": str(e)})
        raise


async def extract_product_info(text: str) -> dict:
    """Use GPT to extract structured product info from a freeform description."""
    config = _load_config()
    client = AsyncOpenAI(api_key=config["openai_api_key"])
    prompt = f"""Extract structured ad-campaign inputs from the user's freeform description.

USER INPUT:
{text}

Respond ONLY with this JSON (no markdown). Make plausible assumptions where info is missing:
{{
  "company_name": "...",
  "company_description": "...",
  "product_name": "...",
  "product_description": "...",
  "target_audience": "...",
  "selling_points": ["...", "...", "..."],
  "brand_colors": "hex codes or descriptive",
  "call_to_action": "...",
  "additional_info": ""
}}"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You extract structured marketing brief data. Respond with JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
