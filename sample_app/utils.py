import bleach
from django.conf import settings

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'a', 'ul', 'ol', 'li', 
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'code',
    'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height', 'class', 'title'],
    'div': ['class'],
    'span': ['class'],
    'table': ['class'],
    'th': ['scope'],
    'td': ['colspan', 'rowspan'],
    'pre': ['class'],
    'code': ['class']
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'data']

def sanitize_html_content(content):
    """
    Sanitize HTML content to prevent XSS attacks while preserving formatting.
    
    Args:
        content (str): Raw HTML content from rich text editor
        
    Returns:
        str: Sanitized HTML content safe for display
    """
    if not content:
        return content
    
    cleaned_content = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True
    )
    
    cleaned_content = bleach.linkify(
        cleaned_content,
        callbacks=[],
        skip_tags=['pre', 'code']
    )
    
    return cleaned_content


def validate_content_security(content):
    """
    Validate content for security issues beyond basic HTML sanitization.
    
    Args:
        content (str): HTML content to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not content:
        return True, None
    
    text_content = bleach.clean(content, tags=[], strip=True)
    if len(text_content.strip()) < 10:
        return False, "Article content must be at least 10 characters long."
    
    suspicious_patterns = [
        'javascript:',
        'vbscript:',
        'data:text/html',
        'onload=',
        'onerror=',
        'onclick=',
        'onmouseover=',
        '<script',
        '</script>',
        'eval(',
        'document.cookie',
        'document.write'
    ]
    
    content_lower = content.lower()
    for pattern in suspicious_patterns:
        if pattern in content_lower:
            return False, f"Content contains potentially unsafe pattern: {pattern}"
    
    if content.count('<') > 1000:
        return False, "Content contains too many HTML tags."
    
    return True, None


def extract_text_preview(html_content, max_length=200):
    """
    Extract plain text preview from HTML content for summaries.
    
    Args:
        html_content (str): HTML content
        max_length (int): Maximum length of preview text
        
    Returns:
        str: Plain text preview
    """
    if not html_content:
        return ""
    
    text = bleach.clean(html_content, tags=[], strip=True)
    
    text = ' '.join(text.split())
    
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
    
    return text


def process_article_content(content):
    """
    Complete processing pipeline for article content.
    
    Args:
        content (str): Raw HTML content from editor
        
    Returns:
        tuple: (processed_content, is_valid, error_message)
    """
    is_valid, error_message = validate_content_security(content)
    if not is_valid:
        return content, False, error_message
    
    sanitized_content = sanitize_html_content(content)
    
    return sanitized_content, True, None


def enhance_content_for_display(content):
    """
    Enhance content for better display (add responsive classes, etc.).
    
    Args:
        content (str): Sanitized HTML content
        
    Returns:
        str: Enhanced HTML content
    """
    if not content:
        return content
    
    content = content.replace('<table', '<table class="table table-bordered table-responsive"')
    
    content = content.replace('<img', '<img class="img-fluid"')
    
    import re
    content = re.sub(
        r'<a\s+([^>]*?)href=["\']https?://(?!localhost|127\.0\.0\.1)([^"\']*)["\']([^>]*?)>',
        r'<a \1href="https://\2"\3 target="_blank" rel="noopener noreferrer">',
        content
    )
    
    return content
