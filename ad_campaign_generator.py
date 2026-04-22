#!/usr/bin/env python3
"""
Ad Campaign Generator
Creates a complete ad campaign (slogan, poster, video) using affordable AI APIs.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import fal_client


def load_config():
    """Load API keys from config file."""
    config_path = Path(__file__).parent / "api_config.json"

    if not config_path.exists():
        print("ERROR: api_config.json not found!")
        print("Please create the file with your API keys.")
        return None

    with open(config_path, "r") as f:
        return json.load(f)


def get_product_info():
    """Load product information from JSON file."""
    json_path = Path(__file__).parent / "product_info.json"

    if not json_path.exists():
        print("ERROR: product_info.json not found!")
        print(f"Please create the file at: {json_path}")
        print("\nSee product_info_example.json for a template.")
        return None

    with open(json_path, "r") as f:
        info = json.load(f)

    # Validate required fields
    required_fields = [
        "company_name",
        "company_description",
        "product_name",
        "product_description",
        "target_audience",
        "selling_points",
        "brand_colors",
        "call_to_action"
    ]

    missing = [field for field in required_fields if field not in info or not info[field]]
    if missing:
        print(f"ERROR: Missing required fields: {', '.join(missing)}")
        return None

    return info


def generate_slogan_and_theme(config, product_info):
    """Generate slogan and overall theme using OpenAI."""
    print("\n" + "-" * 40)
    print("Generating slogan and theme...")
    print("-" * 40)

    client = OpenAI(api_key=config["openai_api_key"])

    prompt = f"""
You are a creative advertising director. Create a compelling ad campaign for:

COMPANY: {product_info['company_name']}
- {product_info['company_description']}

NEW PRODUCT: {product_info['product_name']}
- {product_info['product_description']}

TARGET AUDIENCE: {product_info['target_audience']}

KEY SELLING POINTS:
{chr(10).join('  - ' + p for p in product_info['selling_points'])}

BRAND STYLE: {product_info['brand_colors']}

CALL TO ACTION: {product_info['call_to_action']}

{product_info['additional_info'] if product_info['additional_info'] else ''}

Provide your response in this EXACT JSON format:
{{
    "slogan": "A catchy, memorable slogan (max 10 words)",
    "theme": "Description of the overall visual and emotional theme",
    "tone": "The tone/mood of the campaign (e.g., energetic, sophisticated, playful)",
    "color_palette": "Suggested color palette based on brand preferences",
    "visual_style": "Description of the visual style for the poster and video"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative advertising director. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"Error generating slogan/theme: {e}")
        return None


def generate_poster(config, product_info, campaign_theme):
    """Generate ad poster image using OpenAI's image generation."""
    print("\n" + "-" * 40)
    print("Generating poster image...")
    print("-" * 40)

    client = OpenAI(api_key=config["openai_api_key"])

    image_prompt = f"""Create a professional advertising poster with:

Product: {product_info['product_name']}
Slogan: "{campaign_theme['slogan']}"

Visual Style: {campaign_theme['visual_style']}
Theme: {campaign_theme['theme']}
Color Palette: {campaign_theme['color_palette']}
Tone: {campaign_theme['tone']}

The poster should be eye-catching, professional, and suitable for {product_info['target_audience']}.
Include the product name prominently. Design for a marketing advertisement.
"""

    try:
        response = client.images.generate(
            model="dall-e-2",  # Cheapest OpenAI image model
            prompt=image_prompt,
            size="1024x1024",
            n=1
        )

        return response.data[0].url

    except Exception as e:
        print(f"Error generating poster: {e}")
        return None


def generate_video(config, product_info, campaign_theme):
    """Generate 10-second video ad using Kling AI via fal.ai."""
    print("\n" + "-" * 40)
    print("Generating 10-second video ad...")
    print("-" * 40)
    print("(This may take 2-5 minutes...)")

    video_prompt = f"""Create a 10-second commercial advertisement video:

Product: {product_info['product_name']} from {product_info['company_name']}
Slogan: "{campaign_theme['slogan']}"

Visual Style: {campaign_theme['visual_style']}
Theme: {campaign_theme['theme']}
Color Palette: {campaign_theme['color_palette']}
Tone: {campaign_theme['tone']}

Target Audience: {product_info['target_audience']}

Create a professional, engaging 10-second ad spot that showcases the product
and ends with a clear call to action: "{product_info['call_to_action']}"

Cinematic commercial quality, suitable for social media advertising.
"""

    try:
        # Submit video generation job to Kling via fal.ai
        result = fal_client.submit(
            "fal-ai/kling-video/v1/standard/text-to-video",
            arguments={
                "prompt": video_prompt,
                "duration": 10
            }
        )

        # Wait for completion and get result
        response = result.get()

        # Extract video URL from response
        if response and "video" in response and "url" in response["video"]:
            return response["video"]["url"]
        elif response and "video_url" in response:
            return response["video_url"]
        else:
            print(f"Unexpected response format: {response}")
            return None

    except Exception as e:
        print(f"Error generating video: {e}")
        return None


def download_asset(url, save_path):
    """Download an asset from URL to local file."""
    import requests

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        print(f"Error downloading {save_path}: {e}")
        return False


def save_campaign(output_dir, product_info, campaign_theme, poster_url, video_url):
    """Save all campaign assets and metadata."""

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    campaign_dir = output_dir / f"campaign_{timestamp}"
    campaign_dir.mkdir(parents=True, exist_ok=True)

    saved_files = {}

    # Save slogan and theme
    theme_file = campaign_dir / "slogan_theme.txt"
    with open(theme_file, "w") as f:
        f.write(f"=== AD CAMPAIGN: {product_info['product_name']} ===\n\n")
        f.write(f"SLOGAN: {campaign_theme['slogan']}\n\n")
        f.write(f"THEME: {campaign_theme['theme']}\n\n")
        f.write(f"TONALITY: {campaign_theme['tone']}\n\n")
        f.write(f"COLOR PALETTE: {campaign_theme['color_palette']}\n\n")
        f.write(f"VISUAL STYLE: {campaign_theme['visual_style']}\n")
    saved_files["theme"] = str(theme_file)
    print(f"  Saved: {theme_file}")

    # Download and save poster
    if poster_url:
        poster_file = campaign_dir / "poster.png"
        if download_asset(poster_url, poster_file):
            saved_files["poster"] = str(poster_file)
            print(f"  Saved: {poster_file}")
        else:
            # Save URL as fallback
            with open(campaign_dir / "poster_url.txt", "w") as f:
                f.write(poster_url)
            saved_files["poster_url"] = poster_url
    else:
        saved_files["poster"] = "FAILED"

    # Download and save video
    if video_url:
        video_file = campaign_dir / "ad_video.mp4"
        if download_asset(video_url, video_file):
            saved_files["video"] = str(video_file)
            print(f"  Saved: {video_file}")
        else:
            # Save URL as fallback
            with open(campaign_dir / "video_url.txt", "w") as f:
                f.write(video_url)
            saved_files["video_url"] = video_url
    else:
        saved_files["video"] = "FAILED"

    # Save campaign summary JSON
    summary = {
        "timestamp": timestamp,
        "product_info": product_info,
        "campaign_theme": campaign_theme,
        "generated_files": saved_files
    }

    summary_file = campaign_dir / "campaign_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved: {summary_file}")

    return campaign_dir


def main():
    """Main function to run the ad campaign generator."""
    print("\n" + "=" * 50)
    print("       AI AD CAMPAIGN GENERATOR")
    print("=" * 50)
    print("\nThis tool creates a complete ad campaign using AI:")
    print("  1. Slogan & Theme (GPT-4o-mini)")
    print("  2. Poster Image (GPT Image 1)")
    print("  3. 10-Second Video Ad (Kling AI)")
    print("\nEstimated cost per campaign: ~$0.30-0.50")
    print("=" * 50)

    # Load API configuration
    config = load_config()
    if not config:
        return

    # Validate required keys
    if "openai_api_key" not in config:
        print("ERROR: 'openai_api_key' not found in api_config.json")
        return
    if "fal_api_key" not in config:
        print("ERROR: 'fal_api_key' not found in api_config.json")
        return

    # Set fal.ai API key
    os.environ["FAL_KEY"] = config["fal_api_key"]

    # Get product information from JSON file
    product_info = get_product_info()
    if not product_info:
        return

    print(f"\nGenerating campaign for: {product_info['product_name']}")
    print(f" by: {product_info['company_name']}")
    print("\n" + "=" * 50)
    print("GENERATING CAMPAIGN...")
    print("=" * 50)

    # Step 1: Generate slogan and theme
    campaign_theme = generate_slogan_and_theme(config, product_info)
    if not campaign_theme:
        print("Failed to generate campaign theme. Exiting.")
        return

    print(f"\n SLOGAN: {campaign_theme['slogan']}")
    print(f" THEME: {campaign_theme['theme']}")

    # Step 2: Generate poster
    print("\n Generating poster image...")
    poster_url = generate_poster(config, product_info, campaign_theme)
    if poster_url:
        print("  Poster generated successfully!")
    else:
        print("  Poster generation failed.")

    # Step 3: Generate video
    print("\n Generating 10-second video ad...")
    print("  (This may take 2-5 minutes...)")
    video_url = generate_video(config, product_info, campaign_theme)
    if video_url:
        print("  Video generated successfully!")
    else:
        print("  Video generation failed.")

    # Save all assets
    print("\n" + "-" * 40)
    print("Saving campaign assets...")
    print("-" * 40)

    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    campaign_dir = save_campaign(output_dir, product_info, campaign_theme, poster_url, video_url)

    print("\n" + "=" * 50)
    print("CAMPAIGN COMPLETE!")
    print("=" * 50)
    print(f"\nCampaign saved to: {campaign_dir}")
    print("\nGenerated assets:")
    print(f"  - Slogan & Theme document")
    print(f"  - Poster image")
    print(f"  - 10-second video ad")
    print(f"  - Campaign summary JSON")
    print()


if __name__ == "__main__":
    main()
