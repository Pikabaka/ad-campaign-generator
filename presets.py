"""Style presets — describe AESTHETICS, not brands.

Naming brands directly (e.g. "Apple", "Nike") makes image/video models copy
brand iconography (Apple logos, muscle bros). We describe the visual language
attribute-by-attribute instead, so the model invents fresh imagery.
"""

PRESETS = {
    "apple": {
        "id": "apple",
        "name": "Pure Minimal",
        "emoji": "◯",
        "gradient": "from-slate-200 to-slate-50",
        "visual_style": "Hyper-minimalist studio photography on a seamless pure-white cyclorama. Single hero subject perfectly centered with extreme negative space — at least 70% empty white. Soft directional softbox lighting from upper-left, gentle wraparound shadow. Ultra-sharp focus on the subject only. Crisp geometric sans-serif typography in deep charcoal. No additional graphics, no patterns, no decorative elements, no logos other than the product itself. Premium aspirational tone, like a high-end museum catalogue.",
        "color_palette": "#FFFFFF dominant, #1D1D1F charcoal type, #86868B mid-grey accents",
        "tone": "Calm, premium, aspirational, restrained",
        "music_genre": "Soft ambient piano with subtle airy synth pads, slow sustained chords, contemplative and aspirational",
        "voice": "onyx",
        "voice_instructions": "Calm, deliberate, confident. Speak slowly with full pauses between sentences, as if delivering a quiet keynote to a captivated audience. Lower the voice slightly on the call-to-action for gravitas.",
        "font_hint": "geometric sans-serif"
    },
    "nike": {
        "id": "nike",
        "name": "Athletic Anthem",
        "emoji": "⚡",
        "gradient": "from-orange-500 to-red-600",
        "visual_style": "High-energy action photography with motion blur, dramatic high-contrast rim lighting, dynamic low-angle hero shots, sweat and grit textures. Diverse cast across genders, ages, body types, and ethnicities — explicitly avoid stereotypical bodybuilder imagery; show real people of varied appearances in authentic motion. Documentary realism, raw, unposed. Stark black-and-white tonal range with one bold accent color punching through. Compositions feel like a freeze-frame from a documentary.",
        "color_palette": "#000000, #FFFFFF, single bold accent #FA5400",
        "tone": "Bold, fearless, motivational, raw",
        "music_genre": "Hard-hitting hip hop trap beat with heavy 808s and stadium-anthem energy, fast tempo, motivational",
        "voice": "echo",
        "voice_instructions": "Urgent, intense, motivational. Push energy forward like a sports broadcaster calling the final lap. Slight rasp. Clip the consonants, don't drag the vowels.",
        "font_hint": "ultra-bold condensed sans"
    },
    "cyberpunk": {
        "id": "cyberpunk",
        "name": "Cyberpunk Neon",
        "emoji": "🌃",
        "gradient": "from-fuchsia-600 to-cyan-500",
        "visual_style": "Cyberpunk neon-soaked night scene. Wet asphalt reflecting magenta and cyan signage, holographic interface overlays, dense urban density, fog with volumetric light rays, lens flares, slight chromatic aberration on edges. Cinematic anamorphic widescreen feel. Inspired by 1980s sci-fi noir — futuristic but lived-in, grimy, atmospheric. The product sits as a glowing focal point against this backdrop.",
        "color_palette": "#FF00FF magenta, #00FFFF cyan, #0A0014 deep night, #FFD700 amber accents",
        "tone": "Edgy, futuristic, rebellious, electric",
        "music_genre": "Synthwave with heavy analog synths, pulsing arpeggios, retrofuturistic dark electronic, slow-burn tempo",
        "voice": "nova",
        "voice_instructions": "Cool, detached, slightly synthetic and clipped. Like an AI announcer in a rain-soaked Tokyo subway at 3am. Add micro-pauses between phrases for an uncanny robotic cadence.",
        "font_hint": "monospace / techno display"
    },
    "wes_anderson": {
        "id": "wes_anderson",
        "name": "Symmetric Whimsy",
        "emoji": "🎞️",
        "gradient": "from-rose-300 to-amber-200",
        "visual_style": "Perfectly symmetrical composition with the subject dead-center. Flat frontal staging like a dollhouse cross-section. Pastel macaron color palette: powder pink, mint, mustard, sky blue, butter yellow. Vintage 1960s set design with art-direction-heavy props. Tilt-shift miniature feel. Slight film grain, warm tone. Whimsical, deadpan, storybook quality.",
        "color_palette": "#F8C8DC powder pink, #FFE5B4 butter yellow, #B8DCD8 mint, #E8B5A6 dusty rose",
        "tone": "Whimsical, charming, deadpan, nostalgic",
        "music_genre": "Quirky baroque chamber pop with harpsichord and pizzicato strings, French yé-yé pop influence, whimsical and bittersweet",
        "voice": "shimmer",
        "voice_instructions": "Deadpan but warm, slightly melancholic. Speak with the cadence of a 1960s storybook narrator. Even pacing, no peaks of excitement, gentle wry undertone.",
        "font_hint": "vintage serif slab"
    },
    "y2k": {
        "id": "y2k",
        "name": "Y2K Maximalist",
        "emoji": "💿",
        "gradient": "from-cyan-300 via-pink-300 to-purple-400",
        "visual_style": "Y2K millennium aesthetic with liquid chrome metallic textures, holographic iridescent surfaces, blobby bubble shapes, frosted glass elements, lens flares and sparkle particles. Maximum visual density. Backgrounds layered with gradient meshes and soft-focus bokeh. Inspired by early-2000s pop culture graphic design — futuristic but innocent.",
        "color_palette": "#C0C0C0 chrome silver, #FF6EC7 hot pink, #00E5FF cyan, #B57BFF lavender",
        "tone": "Hyperactive, playful, futuristic-retro, glamorous",
        "music_genre": "Eurodance and 2000s pop with autotuned vocal chops, trance synth leads, peppy bubblegum bass",
        "voice": "shimmer",
        "voice_instructions": "Hyper-energetic, peppy, slightly auto-tuned vibe. Bouncy delivery like a 2003 MTV bumper announcer. Smile through the voice.",
        "font_hint": "rounded chrome bevel sans"
    },
    "k_beauty": {
        "id": "k_beauty",
        "name": "Dewy Soft Glow",
        "emoji": "🌸",
        "gradient": "from-pink-200 to-rose-100",
        "visual_style": "Soft dewy editorial beauty photography. Glowing translucent skin, milky soft pink tones, glass-like surface highlights captured in macro detail. Cherry blossom petals, pearl textures, satin fabric. Ultra-clean studio lighting with diffused white softboxes from all directions. Pastel pink and ivory dominate. Hyper-feminine, delicate, almost weightless aesthetic.",
        "color_palette": "#FFE4EC pale pink, #FFFFFF, #F4B6C2 dusty rose, #FFD7E1",
        "tone": "Tender, dreamy, fresh, gentle",
        "music_genre": "Soft K-pop ballad instrumental with mellow piano and strings, lo-fi dream pop, gentle and aspirational",
        "voice": "alloy",
        "voice_instructions": "Soft, breathy, gentle, almost whispered. Smooth and unhurried. Imagine recommending a beauty ritual to a close friend at midnight.",
        "font_hint": "delicate modern serif"
    },
    "brutalist": {
        "id": "brutalist",
        "name": "Brutalist",
        "emoji": "▦",
        "gradient": "from-zinc-900 to-zinc-700",
        "visual_style": "Brutalist graphic design language. Harsh black-and-white photography. Oversized raw typography overlapping the subject deliberately. Concrete, steel, and exposed-aggregate textures. Stark contrast, deconstructed grid, intentional anti-design — misalignments, asymmetry, rough crops. Documentary photo quality, no retouching. Often a single hard accent color used sparingly.",
        "color_palette": "#000000, #FFFFFF, single hot accent #FF0000",
        "tone": "Raw, unflinching, intellectual, austere",
        "music_genre": "Industrial techno with distorted kick drums, dark minimal techno, warehouse rave intensity",
        "voice": "echo",
        "voice_instructions": "Stark, deliberate, cold. Each word carved out with space around it. No warmth, no apology, no emotional inflection. Almost monotone but with absolute conviction.",
        "font_hint": "Helvetica oversized / monospace"
    },
    "vintage_film": {
        "id": "vintage_film",
        "name": "Vintage Film",
        "emoji": "📷",
        "gradient": "from-amber-700 to-orange-300",
        "visual_style": "1970s film photography aesthetic. Visible Kodak Portra-style grain, warm faded tones, lens flares and light leaks at frame edges, slight halation around highlights. Sun-washed nostalgic feel, golden-hour lighting bias. Cars, fashion, and props evocative of mid-century Americana without being identifiable to a single era. Color shifted slightly cyan-orange.",
        "color_palette": "#D4A574 wheat, #C97B5C terracotta, #6B4423 walnut, #F4E4BC cream",
        "tone": "Nostalgic, warm, sentimental, sun-drenched",
        "music_genre": "Vintage 70s soft rock with warm Rhodes piano, lo-fi soul, gentle acoustic guitar, sun-faded americana",
        "voice": "fable",
        "voice_instructions": "Warm, gravelly, paternal. Speak like a 1970s AM-radio narrator on a summer afternoon. Slight smile in the voice, unhurried, full of memory.",
        "font_hint": "serif / typewriter"
    }
}


def get_preset(preset_id: str):
    """Return preset dict, or None if id not found."""
    return PRESETS.get(preset_id)


def list_presets():
    """Return list of presets for the UI."""
    return list(PRESETS.values())
