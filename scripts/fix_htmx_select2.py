import re

def fix_js_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    changes = []

    # 1. First afterSettle handler (select2 init)
    old1 = '''$(document).on("htmx:afterSettle", function (event) {
    var target = $(event.target);
    target.find(".oh-select").select2({ width: '100%' });

    target.find("select").off("select2:select").on("select2:select", function (e) {
        this.dispatchEvent(new Event("change"));
    });
});'''

    new1 = '''$(document).on("htmx:afterSettle", function (event) {
    try {
        var target = $(event.target);
        if (target && target.find) {
            target.find(".oh-select").select2({ width: '100%' });
            target.find("select").off("select2:select").on("select2:select", function (e) {
                this.dispatchEvent(new Event("change"));
            });
        }
    } catch (error) {
        console.warn("htmxSelect2: afterSettle select2 error:", error);
    }
});'''

    if old1 in content:
        content = content.replace(old1, new1, 1)
        changes.append("First afterSettle handler")
    else:
        print(f"  WARN: First afterSettle pattern NOT FOUND in {filepath}")

    # 2. afterSwap handler
    old2 = '''$(document).on("htmx:afterSwap", async function (evt) {
    if ($('[role="tooltip"]:visible').length) {
        $('[role="tooltip"]').hide();
    }
    cachedInstalledApps = await loadFromLocalStorage();
    // Try loading cached data from localStorage first
    if (cachedInstalledApps) {
        // Use the cached data
        loadScripts(cachedInstalledApps);
    } else {
        // Fetch the data via AJAX if not cached or cache is invalid
        $.ajax({
            url: '/get-skylinx-installed-apps/',
            method: 'GET',
            success: async function (response) {
                cachedInstalledApps = response.installed_apps;
                await saveToLocalStorage(cachedInstalledApps);
                loadScripts(cachedInstalledApps);
            },
            error: function (error) {
                console.error("Error fetching installed apps:", error);
            }
        });
    }
});'''

    new2 = '''$(document).on("htmx:afterSwap", async function (evt) {
    try {
        if ($('[role="tooltip"]:visible').length) {
            $('[role="tooltip"]').hide();
        }
        cachedInstalledApps = await loadFromLocalStorage();
        // Try loading cached data from localStorage first
        if (cachedInstalledApps) {
            // Use the cached data
            loadScripts(cachedInstalledApps);
        } else {
            // Fetch the data via AJAX if not cached or cache is invalid
            $.ajax({
                url: '/get-skylinx-installed-apps/',
                method: 'GET',
                success: async function (response) {
                    cachedInstalledApps = response.installed_apps;
                    await saveToLocalStorage(cachedInstalledApps);
                    loadScripts(cachedInstalledApps);
                },
                error: function (error) {
                    console.error("Error fetching installed apps:", error);
                }
            });
        }
    } catch (error) {
        console.warn("htmxSelect2: afterSwap error:", error);
    }
});'''

    if old2 in content:
        content = content.replace(old2, new2, 1)
        changes.append("afterSwap handler")
    else:
        print(f"  WARN: afterSwap pattern NOT FOUND in {filepath}")

    # 3. Second afterSettle handler (UI bindings) - wrap entire body in try-catch
    # Need to find the opening and closing
    pattern_start = '$(document).on("htmx:afterSettle", function (e) {'
    last_idx = content.rfind(pattern_start)
    if last_idx >= 0:
        # Insert try { after the opening brace
        insert_pos = last_idx + len(pattern_start)
        before = content[:insert_pos]
        after = content[insert_pos:]
        
        # The body currently starts right after the opening brace (newline)
        # We need to add "try {" after the opening brace
        before += "\n    try {"
        
        # Find the closing }); at the end - it's the last }); in the file
        # Find the last occurrence of \n}); that closes this handler
        # Since it's the last handler, we can find the last });
        last_close = content.rfind("\n});")
        if last_close >= 0:
            # The close is relative to original content, but we've already split
            # so we need to calculate the position in the 'after' portion
            close_in_after = after.rfind("\n});")
            if close_in_after >= 0:
                catch_block = "\n    } catch (error) {\n        console.warn(\"htmxSelect2: afterSettle UI error:\", error);\n    }"
                after = after[:close_in_after] + catch_block + after[close_in_after:]
                content = before + after
                changes.append("Second afterSettle handler")
        else:
            print(f"  WARN: Could not find closing for second handler in {filepath}")
    else:
        print(f"  WARN: Second afterSettle pattern NOT FOUND in {filepath}")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  Applied {len(changes)} changes to {filepath}: {', '.join(changes)}")


# Fix both files
print("Fixing static/build/js/htmxSelect2.js...")
fix_js_file('static/build/js/htmxSelect2.js')

print("\nFixing skylinx_theme/static/skylinx_theme/assets/js/htmxSelect2.js...")
fix_js_file('skylinx_theme/static/skylinx_theme/assets/js/htmxSelect2.js')

print("\nDone!")
