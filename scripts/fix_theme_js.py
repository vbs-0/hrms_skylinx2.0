"""Fix the first afterSettle handler in theme's htmxSelect2.js"""
with open('skylinx_theme/static/skylinx_theme/assets/js/htmxSelect2.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the first afterSettle handler 
marker = '$(document).on("htmx:afterSettle", function (event) {'
idx = content.find(marker)
if idx >= 0:
    # Find the end of this handler (first }); after the opening)
    start = idx
    # Find the closing }); - it's the first }); that matches
    after_start = content[idx+len(marker):]
    # Count braces to find the matching closing
    depth = 1
    handler_end = 0
    i = 0
    while depth > 0 and i < len(after_start):
        if after_start[i] == '{':
            depth += 1
        elif after_start[i] == '}':
            depth -= 1
        i += 1
    
    # Now we're at the } that closes the function body
    # The handler ends with }); so we need to find the next ); after the brace
    close_brace_pos = idx + len(marker) + i
    
    old_handler = content[idx:close_brace_pos]
    
    # New handler with try-catch
    inner_body_start = content[idx+len(marker):close_brace_pos]
    # Remove the outer braces
    inner_body = inner_body_start.strip()[1:-1].strip()
    
    new_handler = '''$(document).on("htmx:afterSettle", function (event) {
    try {
        var target = $(event.target);
        if (target && target.find) {
            target.find(".oh-select").each(function () {
                if ($(this).data('select2')) {
                    $(this).select2("destroy");
                }
                $(this).select2({ width: '100%' });
            });
            target.find("select").off("select2:select").on("select2:select", function (e) {
                this.dispatchEvent(new Event("change"));
            });
        }
    } catch (error) {
        console.warn("htmxSelect2: afterSettle select2 error:", error);
    }
});'''
    
    content = content[:idx] + new_handler + content[close_brace_pos:]
    print("First afterSettle handler fixed in theme file")
else:
    print("Marker not found!")
    # Try to find it
    print(repr(content[content.find('afterSettle')-20:content.find('afterSettle')+150]))

with open('skylinx_theme/static/skylinx_theme/assets/js/htmxSelect2.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
