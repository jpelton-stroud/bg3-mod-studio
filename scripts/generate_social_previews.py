#!/usr/bin/env python3
import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH = 1280
HEIGHT = 640

# Font paths
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

def create_radial_gradient(width, height, center_x, center_y, inner_color, outer_color, radius):
    """Generates a soft radial glow image."""
    base = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    # Render at lower resolution and upscale for super smooth gradient
    scale = 4
    sw, sh = width // scale, height // scale
    cx, cy = center_x / scale, center_y / scale
    r = radius / scale
    
    img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    pixels = img.load()
    
    ir, ig, ib, ia = inner_color
    or_, og, ob, oa = outer_color
    
    for y in range(sh):
        for x in range(sw):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            t = min(1.0, max(0.0, dist / r))
            # Smoothstep
            t = t * t * (3 - 2 * t)
            cur_r = int(ir + (or_ - ir) * t)
            cur_g = int(ig + (og - ig) * t)
            cur_b = int(ib + (ob - ib) * t)
            cur_a = int(ia + (oa - ia) * t)
            pixels[x, y] = (cur_r, cur_g, cur_b, cur_a)
            
    base = img.resize((width, height), Image.Resampling.BICUBIC)
    return base

def draw_ornate_border(draw, width, height, inset=24, color=(212, 175, 55, 140), corner_size=28):
    """Draws a fantasy D&D / Baldur's Gate style gold border with corner accents."""
    x0, y0 = inset, inset
    x1, y1 = width - inset, height - inset
    
    # Outer thin border
    draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
    # Inner subtle border
    draw.rectangle([x0 + 6, y0 + 6, x1 - 6, y1 - 6], outline=(color[0], color[1], color[2], 60), width=1)
    
    # Corner diamonds / flourishes
    for cx, cy in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
        # Corner diamond
        draw.polygon([
            (cx, cy - 8),
            (cx + 8, cy),
            (cx, cy + 8),
            (cx - 8, cy)
        ], fill=(245, 215, 110, 220), outline=color)
        
        # Corner brackets
        sign_x = 1 if cx == x0 else -1
        sign_y = 1 if cy == y0 else -1
        draw.line([(cx + sign_x * 4, cy + sign_y * 14), (cx + sign_x * 14, cy + sign_y * 14), (cx + sign_x * 14, cy + sign_y * 4)], fill=color, width=2)

def draw_badge(draw, text, xy, font, bg_color=(25, 30, 45, 230), border_color=(212, 175, 55, 180), text_color=(240, 240, 240, 255), pad=(14, 7)):
    x, y = xy
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    bx0 = x
    by0 = y
    bx1 = x + tw + pad[0] * 2
    by1 = y + th + pad[1] * 2
    
    # Rounded badge box
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=6, fill=bg_color, outline=border_color, width=1)
    # Text
    draw.text((bx0 + pad[0], by0 + pad[1] - bbox[1]), text, font=font, fill=text_color)
    return bx1 - bx0

def draw_d20(draw, cx, cy, radius, color=(212, 175, 55, 200), fill_color=(20, 25, 40, 180)):
    """Draws an authentic geometric 20-sided die (Icosahedron projection)."""
    # Outer hexagon
    hex_pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        hex_pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    
    # Inner triangle
    tri_r = radius * 0.58
    tri_pts = []
    for i in range(3):
        angle = math.radians(120 * i - 90)
        tri_pts.append((cx + tri_r * math.cos(angle), cy + tri_r * math.sin(angle)))
        
    # Draw background polygon
    draw.polygon(hex_pts, fill=fill_color, outline=color, width=3)
    
    # Draw inner triangle
    draw.polygon(tri_pts, fill=(fill_color[0]+15, fill_color[1]+15, fill_color[2]+25, 220), outline=color, width=2)
    
    # Connect inner triangle vertices to outer hexagon
    draw.line([tri_pts[0], hex_pts[0]], fill=color, width=2)
    draw.line([tri_pts[0], hex_pts[5]], fill=color, width=2)
    
    draw.line([tri_pts[1], hex_pts[1]], fill=color, width=2)
    draw.line([tri_pts[1], hex_pts[2]], fill=color, width=2)
    
    draw.line([tri_pts[2], hex_pts[3]], fill=color, width=2)
    draw.line([tri_pts[2], hex_pts[4]], fill=color, width=2)

# ==========================================
# CARD 1: Core Project Showcase (Hero)
# ==========================================
def render_card_1(output_path):
    print("Generating Card 1: Core Project Showcase...")
    # Base dark fantasy gradient (Deep obsidian navy to abyssal crimson-purple)
    im = Image.new("RGBA", (WIDTH, HEIGHT), (11, 14, 22, 255))
    
    # Ambient glows
    glow1 = create_radial_gradient(WIDTH, HEIGHT, 280, 220, (180, 50, 30, 95), (0, 0, 0, 0), 450) # Crimson astral glow
    glow2 = create_radial_gradient(WIDTH, HEIGHT, 980, 420, (212, 175, 55, 75), (0, 0, 0, 0), 500) # Gold celestial glow
    glow3 = create_radial_gradient(WIDTH, HEIGHT, 640, 100, (60, 30, 90, 80), (0, 0, 0, 0), 600)  # Illithid purple
    
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im = Image.alpha_composite(im, glow3)
    
    draw = ImageDraw.Draw(im)
    
    # Subtle geometric astral / tech grid lines in background
    for x in range(60, WIDTH, 120):
        draw.line([(x, 30), (x, HEIGHT - 30)], fill=(212, 175, 55, 12), width=1)
    for y in range(40, HEIGHT, 100):
        draw.line([(30, y), (WIDTH - 30, y)], fill=(212, 175, 55, 12), width=1)
        
    # Mystic circles & D20 watermark on right side
    d20_cx, d20_cy = 980, 320
    draw.ellipse([d20_cx - 180, d20_cy - 180, d20_cx + 180, d20_cy + 180], outline=(212, 175, 55, 30), width=2)
    draw.ellipse([d20_cx - 220, d20_cy - 220, d20_cx + 220, d20_cy + 220], outline=(212, 175, 55, 18), width=1)
    draw_d20(draw, d20_cx, d20_cy, 125, color=(245, 205, 90, 210), fill_color=(18, 22, 35, 190))
    
    # Draw ornate border
    draw_ornate_border(draw, WIDTH, HEIGHT, inset=28, color=(212, 175, 55, 170))
    
    # Fonts
    font_eyebrow = ImageFont.truetype(FONT_MONO, 18)
    font_title = ImageFont.truetype(FONT_SERIF_BOLD, 54)
    font_subtitle = ImageFont.truetype(FONT_SANS_BOLD, 26)
    font_desc = ImageFont.truetype(FONT_SANS, 19)
    font_badge = ImageFont.truetype(FONT_MONO, 14)
    
    # Eyebrow / Tag
    draw.text((90, 115), "AN AUTONOMOUS AGENTIC STUDIO", font=font_eyebrow, fill=(245, 195, 80, 230))
    draw.line([(90, 145), (420, 145)], fill=(212, 175, 55, 160), width=2)
    
    # Main Title
    # Shadow
    draw.text((92, 164), "BALDUR'S GATE 3", font=font_title, fill=(0, 0, 0, 220))
    draw.text((90, 162), "BALDUR'S GATE 3", font=font_title, fill=(255, 245, 220, 255))
    
    draw.text((92, 232), "MOD STUDIO & TOOLKIT", font=font_title, fill=(0, 0, 0, 220))
    draw.text((90, 230), "MOD STUDIO & TOOLKIT", font=font_title, fill=(235, 195, 75, 255))
    
    # Subtitle
    draw.text((90, 310), "Architect, Catalog & Theorycraft with AI Pair-Programming", font=font_subtitle, fill=(215, 225, 240, 240))
    
    # Description lines
    desc_p1 = "Autonomous end-to-end workflows for discovery, character progression,"
    desc_p2 = "conflict audits, and native Larian Toolkit mod authorship."
    draw.text((90, 360), desc_p1, font=font_desc, fill=(160, 175, 195, 230))
    draw.text((90, 390), desc_p2, font=font_desc, fill=(160, 175, 195, 230))
    
    # Feature Badges
    badges = [
        ("✦ MOD.IO SYNC", (40, 30, 20, 230), (220, 140, 40, 220)),
        ("✦ LEVEL 1-20 BUILDS", (20, 35, 45, 230), (60, 170, 220, 220)),
        ("✦ CONFLICT DETECTION", (45, 20, 30, 230), (220, 80, 100, 220)),
        ("✦ AGENTIC SCAFFOLDING", (30, 25, 50, 230), (160, 110, 230, 220)),
    ]
    cur_x = 90
    cur_y = 455
    for btext, bg, border in badges:
        bw = draw_badge(draw, btext, (cur_x, cur_y), font_badge, bg_color=bg, border_color=border, text_color=(240, 245, 255, 255))
        cur_x += bw + 15
        
    # Footer metadata info
    draw.text((90, 545), "Cross-Platform: PC • Steam Deck • PlayStation 5 • Xbox Series X|S", font=font_badge, fill=(130, 145, 165, 210))
    draw.text((90, 570), "Built for mod.io REST v1 • Larian Patch 8 Modding Engine", font=font_badge, fill=(110, 125, 145, 190))
    
    im.save(output_path, "PNG")
    print(f"Saved: {output_path}")

# ==========================================
# CARD 2: Agentic Mod Engineering & CLI / Code
# ==========================================
def render_card_2(output_path):
    print("Generating Card 2: Agentic Architecture & Modding Engine...")
    im = Image.new("RGBA", (WIDTH, HEIGHT), (10, 12, 18, 255))
    
    # Subtle teal/cyan & arcane amber background glow
    glow1 = create_radial_gradient(WIDTH, HEIGHT, 220, 480, (20, 90, 120, 80), (0, 0, 0, 0), 480)
    glow2 = create_radial_gradient(WIDTH, HEIGHT, 860, 220, (160, 100, 30, 75), (0, 0, 0, 0), 500)
    glow3 = create_radial_gradient(WIDTH, HEIGHT, 640, 550, (30, 20, 60, 80), (0, 0, 0, 0), 450)
    
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im = Image.alpha_composite(im, glow3)
    
    draw = ImageDraw.Draw(im)
    draw_ornate_border(draw, WIDTH, HEIGHT, inset=26, color=(200, 165, 60, 150))
    
    # Fonts
    font_header = ImageFont.truetype(FONT_SERIF_BOLD, 38)
    font_sub = ImageFont.truetype(FONT_SANS_BOLD, 20)
    font_mono = ImageFont.truetype(FONT_MONO, 15)
    font_code = ImageFont.truetype(FONT_MONO, 13)
    font_badge = ImageFont.truetype(FONT_MONO, 13)
    
    # Top banner
    draw.text((80, 55), "AUTONOMOUS MOD ARCHITECTURE & TOOLKIT", font=font_header, fill=(255, 235, 175, 255))
    draw.text((80, 102), "Specialized Multi-Agent Workflows & High-Precision Automation", font=font_sub, fill=(150, 175, 205, 240))
    
    # Two main visual panels: Left = Agent Command Center, Right = Code / Terminal Execution
    # Panel Left
    p1_box = [80, 150, 580, 560]
    draw.rounded_rectangle(p1_box, radius=10, fill=(16, 20, 30, 220), outline=(212, 175, 55, 120), width=1)
    
    draw.text((105, 175), "⚡ AGENTIC ORCHESTRATION", font=font_mono, fill=(245, 195, 80, 255))
    draw.line([(105, 202), (555, 202)], fill=(212, 175, 55, 70), width=1)
    
    commands = [
        ("/bg3_create_mod", "Scaffold, author & sync custom Larian mods", (160, 110, 240, 255)),
        ("/bg3_search_mods", "Smart semantic query & compatibility filters", (60, 180, 240, 255)),
        ("/bg3_check_mod_conflicts", "Deep AST & UUID collision detection", (240, 90, 110, 255)),
        ("/bg3_create_build_guide", "Lvl 1-20 multi-class & BiS gear optimization", (245, 195, 75, 255)),
        ("/bg3_manage_load_order", "Direct modsettings.lsx priority control", (75, 210, 150, 255)),
    ]
    
    cy = 220
    for cmd, desc, col in commands:
        draw_badge(draw, cmd, (105, cy), font_code, bg_color=(25, 32, 48, 230), border_color=(col[0], col[1], col[2], 180), text_color=col)
        draw.text((105, cy + 34), desc, font=font_code, fill=(170, 185, 205, 230))
        cy += 64
        
    # Panel Right: Interactive Code / Scaffolding Terminal
    p2_box = [610, 150, 1200, 560]
    draw.rounded_rectangle(p2_box, radius=10, fill=(12, 15, 24, 235), outline=(60, 140, 200, 130), width=1)
    
    # Terminal header
    draw.rounded_rectangle([610, 150, 1200, 192], radius=10, fill=(22, 28, 42, 255), outline=(60, 140, 200, 130), width=1)
    # Window dots
    draw.ellipse([628, 167, 638, 177], fill=(230, 80, 80, 255))
    draw.ellipse([646, 167, 656, 177], fill=(240, 180, 60, 255))
    draw.ellipse([664, 167, 674, 177], fill=(60, 190, 100, 255))
    draw.text((700, 164), "bg3-mod-studio: engine_pipeline.py", font=font_code, fill=(150, 170, 200, 220))
    
    code_lines = [
        ("$ python3 scripts/create_mod_scaffold.py \\", (180, 200, 230, 240)),
        ("    --name \"Oath of the Astral Sentinel\" \\", (245, 195, 80, 240)),
        ("    --author \"AgenticStudio\" --version 1.0.0.0", (245, 195, 80, 240)),
        ("", (0,0,0,0)),
        ("[✓] Computed Larian Version64: 36028797018963968", (60, 210, 140, 255)),
        ("[✓] Scaffolded package UUID: 8e4f1a23-bc90-41fa-8a12", (60, 210, 140, 255)),
        ("[✓] Generated meta.lsx, CharacterCreation & SpellData", (60, 210, 140, 255)),
        ("[✓] Created zero-dependency 512x512 mod icon", (60, 210, 140, 255)),
        ("[✓] Hot-synced to Baldur's Gate 3 Data/ directory", (70, 180, 245, 255)),
        ("", (0,0,0,0)),
        (">>> READY FOR LARIAN TOOLKIT PUBLISHING", (235, 195, 75, 255)),
    ]
    
    term_y = 210
    for line, col in code_lines:
        if line:
            draw.text((630, term_y), line, font=font_code, fill=col)
        term_y += 27
        
    # Bottom tech badges on right panel
    badge_x = 630
    for tbadge in ["Python 3.10+", "mod.io REST v1", "Larian Patch 7", "WSL / Linux / Win"]:
        bw = draw_badge(draw, tbadge, (badge_x, 508), font_badge, bg_color=(20, 26, 38, 230), border_color=(212, 175, 55, 100), text_color=(190, 205, 225, 255))
        badge_x += bw + 12
        
    im.save(output_path, "PNG")
    print(f"Saved: {output_path}")

# ==========================================
# CARD 3: Modded Theorycrafting & Gear Catalog
# ==========================================
def render_card_3(output_path):
    print("Generating Card 3: Theorycrafting & Build Guides...")
    im = Image.new("RGBA", (WIDTH, HEIGHT), (12, 10, 20, 255))
    
    # Deep astral violet & radiant gold glows
    glow1 = create_radial_gradient(WIDTH, HEIGHT, 240, 240, (110, 40, 140, 90), (0, 0, 0, 0), 500)
    glow2 = create_radial_gradient(WIDTH, HEIGHT, 1020, 360, (212, 175, 55, 80), (0, 0, 0, 0), 480)
    glow3 = create_radial_gradient(WIDTH, HEIGHT, 640, 120, (180, 45, 60, 65), (0, 0, 0, 0), 550)
    
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im = Image.alpha_composite(im, glow3)
    
    draw = ImageDraw.Draw(im)
    draw_ornate_border(draw, WIDTH, HEIGHT, inset=26, color=(220, 180, 70, 160))
    
    # Fonts
    font_header = ImageFont.truetype(FONT_SERIF_BOLD, 42)
    font_sub = ImageFont.truetype(FONT_SANS_BOLD, 22)
    font_body = ImageFont.truetype(FONT_SANS, 16)
    font_mono = ImageFont.truetype(FONT_MONO, 14)
    font_tag = ImageFont.truetype(FONT_MONO, 12)
    
    # Top Header
    draw.text((80, 60), "LEVEL 1–20 MODDED THEORYCRAFTING", font=font_header, fill=(255, 240, 210, 255))
    draw.text((80, 114), "Precision Combat Sequences, Best-in-Slot Cataloging & Multi-Class Synergies", font=font_sub, fill=(225, 195, 120, 240))
    
    # Three Feature Cards across bottom
    cards = [
        {
            "icon": "⚔️",
            "title": "Level 1–20 Progression",
            "desc": "Architect expanded multiclass leveling tables with UnlockLevelCurve integration and granular feat allocations.",
            "meta": "20-Level Matrix • Feat Synergies",
            "color": (212, 175, 55)
        },
        {
            "icon": "🛡️",
            "title": "Catalog-Wide BiS Gear",
            "desc": "Real-time semantic queries against documented community mod archives to find ideal weapons, armor, and passives.",
            "meta": "Automated Library Search",
            "color": (80, 180, 240)
        },
        {
            "icon": "⚡",
            "title": "Turn 1 Combat Opener",
            "desc": "Strict action economy choreography optimizing bonus actions, reactions, spell slots, and critical damage burst.",
            "meta": "Tactical Sequence Engine",
            "color": (230, 95, 125)
        }
    ]
    
    card_w = 345
    card_h = 320
    gap = 42
    start_x = 80
    start_y = 175
    
    for i, c in enumerate(cards):
        cx = start_x + i * (card_w + gap)
        cy = start_y
        
        # Background box
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=10, fill=(18, 16, 28, 225), outline=(c["color"][0], c["color"][1], c["color"][2], 140), width=1)
        
        # Accent top bar
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + 8], radius=4, fill=(c["color"][0], c["color"][1], c["color"][2], 230))
        
        # Title
        draw.text((cx + 20, cy + 30), c["title"], font=ImageFont.truetype(FONT_SERIF_BOLD, 21), fill=(250, 245, 235, 255))
        
        # Divider
        draw.line([(cx + 20, cy + 65), (cx + card_w - 20, cy + 65)], fill=(212, 175, 55, 60), width=1)
        
        # Description (Word wrap roughly)
        words = c["desc"].split()
        lines = []
        cur_line = []
        for w in words:
            cur_line.append(w)
            if len(" ".join(cur_line)) > 30:
                lines.append(" ".join(cur_line))
                cur_line = []
        if cur_line:
            lines.append(" ".join(cur_line))
            
        text_y = cy + 85
        for line in lines:
            draw.text((cx + 20, text_y), line, font=font_body, fill=(175, 180, 200, 240))
            text_y += 24
            
        # Meta badge at bottom
        draw_badge(draw, c["meta"], (cx + 20, cy + card_h - 48), font_tag, 
                   bg_color=(25, 22, 38, 240), 
                   border_color=(c["color"][0], c["color"][1], c["color"][2], 180), 
                   text_color=(c["color"][0], c["color"][1], c["color"][2], 255),
                   pad=(10, 5))
        
    # Footer tag
    draw.text((80, 540), "✦ Optimized for Community Mods & Official Larian Patch 7 Ecosystem", font=font_mono, fill=(180, 165, 130, 210))
    draw.text((80, 568), "Powered by Autonomous Multi-Agent Workflows & BG3 Mod Studio", font=font_mono, fill=(140, 135, 120, 180))
    
    im.save(output_path, "PNG")
    print(f"Saved: {output_path}")

if __name__ == "__main__":
    out_dir = "/home/jpstroud/projects/BaldursGate3/docs/assets"
    os.makedirs(out_dir, exist_ok=True)
    render_card_1(os.path.join(out_dir, "social-preview-main.png"))
    render_card_2(os.path.join(out_dir, "social-preview-engine.png"))
    render_card_3(os.path.join(out_dir, "social-preview-builds.png"))
