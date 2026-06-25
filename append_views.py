import os

views_path = r'c:\Users\chbha\Desktop\skylinx\HRMS2.0\base\views.py'
content_to_append = '''

from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
from django.http import JsonResponse

@csrf_exempt
def legal_editor(request):
    legal_dir = os.path.join(settings.BASE_DIR, 'base', 'templates', 'legal')
    md_dir = os.path.join(legal_dir, 'md')
    os.makedirs(md_dir, exist_ok=True)
    
    docs = ['privacy_policy', 'terms_and_conditions', 'user_agreement']
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            doc_type = data.get('type')
            markdown = data.get('markdown')
            html = data.get('html')
            
            if doc_type in docs:
                # Save markdown
                md_path = os.path.join(md_dir, f"{doc_type}.md")
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                
                # Regenerate template
                template_path = os.path.join(legal_dir, f"{doc_type}.html")
                
                title_map = {
                    'privacy_policy': 'Privacy Policy',
                    'terms_and_conditions': 'Terms & Conditions',
                    'user_agreement': 'User Agreement'
                }
                
                template_content = f"""{{% load static %}} {{% load i18n %}} <!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'/><meta name='viewport' content='width=device-width, initial-scale=1.0'/><title>SkyLinx Legal</title><link rel='stylesheet' href='{{% static 'build/css/style.min.css' %}}' /><link rel='stylesheet' href='{{% static 'css/skylinx-redesign.css' %}}' /><style>body {{ font-family: 'Plus Jakarta Sans', system-ui, sans-serif; background: #f8fafc; color: #334155; line-height: 1.6; }} .legal-container {{ max-width: 800px; margin: 40px auto; padding: 40px; background: #fff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }} .legal-container h1 {{ font-size: 32px; font-weight: 800; margin-bottom: 24px; color: #0f172a; }} .legal-container h2 {{ font-size: 24px; font-weight: 700; margin-top: 32px; margin-bottom: 16px; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }} .legal-container h3 {{ font-size: 18px; font-weight: 600; margin-top: 24px; margin-bottom: 12px; }} .legal-container p {{ margin-bottom: 16px; }} .legal-container table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }} .legal-container th, .legal-container td {{ border: 1px solid #e2e8f0; padding: 12px; text-align: left; }} .legal-container th {{ background: #f1f5f9; font-weight: 600; }} .back-link {{ display: inline-block; margin-bottom: 24px; color: #2563eb; text-decoration: none; font-weight: 500; }} .back-link:hover {{ text-decoration: underline; }}</style></head><body><div class='legal-container'><a href='/' class='back-link'>&larr; Back to Home</a><div><h1>{title_map[doc_type]}</h1>\\n{html}\\n</div></div></body></html>"""
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(template_content)
                    
                return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    md_contents = {}
    for doc in docs:
        md_path = os.path.join(md_dir, f"{doc}.md")
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                md_contents[doc] = f.read()
        else:
            artifact_path = os.path.join(settings.BASE_DIR, '..', '..', '.gemini', 'antigravity-ide', 'brain', '951b4942-01f5-4571-a457-613a6019603e', f"{doc}.md")
            if os.path.exists(artifact_path):
                with open(artifact_path, 'r', encoding='utf-8') as f:
                    md_contents[doc] = f.read()
            else:
                md_contents[doc] = ""
                
    return render(request, "legal/editor.html", {"md_contents": md_contents})
'''

with open(views_path, 'a', encoding='utf-8') as f:
    f.write(content_to_append)

print("Views updated successfully.")
