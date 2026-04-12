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
                r'<div style="text-align: center;"><a href="\1" style="display: inline-block; padding: 14px 28px; background-color: #001A70; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px; margin-bottom: 15px; font-size: 16px;">Book Now</a></div>', 
                line_stripped
            )
        html_paragraphs.append(f'<p style="margin: 0 0 10px 0;">{line_stripped}</p>')
        
    content = '\n'.join(html_paragraphs)
    
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F4F6F9; padding: 40px 20px; color: #1F2937;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E5E7EB;">
            <div style="background-color: #6B7280; color: #FFD700; padding: 24px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 0.5px;">
                Eurostar Snap Tracker
            </div>
            <div style="padding: 32px 24px; font-size: 16px; line-height: 1.6;">
                {content}
            </div>
            <div style="background-color: #F9FAFB; padding: 20px; text-align: center; font-size: 12px; color: #6B7280; border-top: 1px solid #E5E7EB;">
                You are receiving this because you subscribed to train alerts.<br> Reply STOP to cancel at any time.
            </div>
        </div>
    </div>
    """
    return html