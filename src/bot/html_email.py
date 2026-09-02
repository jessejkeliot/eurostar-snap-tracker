import argparse
import re

from src.bot import msg_templates

# Brand style variables from the style guide
FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
PRIMARY_HEADER_BG = "#001A70"
CTA_BUTTON_BG = "#001A70"
CTA_BUTTON_COLOR = "ghostwhite"
ACCENT_YELLOW = "gold"
BACKGROUND_COLOR = "#F4F6F9"
CARD_BG = "#FFFFFF"
SUBTLE_BACKGROUND = "#F9FAFB"
BORDER_COLOR = "#E5E7EB"
TEXT_PRIMARY = "#1F2937"
TEXT_SECONDARY = "#6B7280"
CARD_BORDER_RADIUS = "8px"
CARD_SHADOW = "0 4px 6px rgba(0,0,0,0.05)"
HEADER_FONT_SIZE = "24px"
HEADER_PADDING = "24px"
BODY_FONT_SIZE = "16px"
BODY_LINE_HEIGHT = "1.6"
BODY_PADDING = "32px 24px"
FOOTER_PADDING = "20px"
BUTTON_PADDING = "14px 28px"
BUTTON_BORDER_RADIUS = "6px"
BUTTON_FONT_SIZE = "16px"
BUTTON_MARGIN_TOP = "15px"
BUTTON_MARGIN_BOTTOM = "15px"
BUTTON_FONT_WEIGHT = "bold"

BUTTON_STYLE = (
    f"display: inline-block; padding: {BUTTON_PADDING}; background-color: {CTA_BUTTON_BG}; "
    f"color: {CTA_BUTTON_COLOR}; text-decoration: none; border-radius: {BUTTON_BORDER_RADIUS}; "
    f"font-weight: {BUTTON_FONT_WEIGHT}; margin-top: {BUTTON_MARGIN_TOP}; "
    f"margin-bottom: {BUTTON_MARGIN_BOTTOM}; font-size: {BUTTON_FONT_SIZE};"
)

CONTAINER_STYLE = (
    f"font-family: {FONT_FAMILY}; background-color: {BACKGROUND_COLOR}; "
    f"padding: 40px 20px; color: {TEXT_PRIMARY};"
)

CARD_STYLE = (
    f"max-width: 600px; margin: 0 auto; background-color: {CARD_BG}; "
    f"border-radius: {CARD_BORDER_RADIUS}; overflow: hidden; box-shadow: {CARD_SHADOW}; "
    f"border: 1px solid {BORDER_COLOR};"
)

HEADER_STYLE = (
    f"background-color: {PRIMARY_HEADER_BG}; color: {CTA_BUTTON_COLOR}; "
    f"padding: {HEADER_PADDING}; text-align: center; font-size: {HEADER_FONT_SIZE}; "
    "font-weight: bold; letter-spacing: 0.5px;"
)

BODY_STYLE = (
    f"padding: {BODY_PADDING}; font-size: {BODY_FONT_SIZE}; "
    f"line-height: {BODY_LINE_HEIGHT};"
)

FOOTER_STYLE = (
    f"background-color: {SUBTLE_BACKGROUND}; padding: {FOOTER_PADDING}; "
    "text-align: center; font-size: 12px; "
    f"color: {TEXT_SECONDARY}; border-top: 1px solid {BORDER_COLOR};"
)


def generate_html_email(subject, body):
    lines = body.split('\n')
    html_paragraphs = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            html_paragraphs.append('<br>')
            continue

        # Convert any raw URL into a big styled CTA button
        if 'http' in line_stripped:
            line_stripped = re.sub(
                r'(https?://[^\s]+)',
                f'<div style="text-align: center;"><a href="\\1" style="{BUTTON_STYLE}">Book Now</a></div>',
                line_stripped,
            )

        html_paragraphs.append(f'<p style="margin: 0 0 10px 0;">{line_stripped}</p>')

    content = '\n'.join(html_paragraphs)

    html = f"""
    <div style="{CONTAINER_STYLE}">
        <div style="{CARD_STYLE}">
            <div style="{HEADER_STYLE}">
                Eurostar Snap Tracker
            </div>
            <div style="{BODY_STYLE}">
                {content}
            </div>
            <div style="{FOOTER_STYLE}">
                You are receiving this because you subscribed to train alerts.<br> Reply STOP to cancel at any time.
            </div>
        </div>
    </div>
    """
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a message about train bookings")
    parser.add_argument("message", nargs="?", default=msg_templates.premium_upgrade()[1], help="Message to parse")

    args = parser.parse_args()
    html = generate_html_email("Email Template", args.message)
    with open("example_email.html", "w") as f:
        f.write(html)
        
        

    