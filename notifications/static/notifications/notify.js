var notify_state = window.__skylinxNotifyState || (window.__skylinxNotifyState = {
    badge_class: "",
    menu_class: "",
    api_url: "",
    fetch_count: 5,
    unread_url: "",
    mark_all_unread_url: "",
    refresh_period: 15000,
    mark_as_read: false,
    consecutive_misfires: 0,
    registered_functions: [],
    poll_timer: null,
    started: false,
});

var notify_badge_class = notify_state.badge_class;
var notify_menu_class = notify_state.menu_class;
var notify_api_url = notify_state.api_url;
var notify_fetch_count = notify_state.fetch_count;
var notify_unread_url = notify_state.unread_url;
var notify_mark_all_unread_url = notify_state.mark_all_unread_url;
var notify_refresh_period = notify_state.refresh_period;
// Set notify_mark_as_read to true to mark notifications as read when fetched
var notify_mark_as_read = notify_state.mark_as_read;

function sync_state() {
    notify_state.badge_class = notify_badge_class;
    notify_state.menu_class = notify_menu_class;
    notify_state.api_url = notify_api_url;
    notify_state.fetch_count = notify_fetch_count;
    notify_state.unread_url = notify_unread_url;
    notify_state.mark_all_unread_url = notify_mark_all_unread_url;
    notify_state.refresh_period = notify_refresh_period;
    notify_state.mark_as_read = notify_mark_as_read;
}

sync_state();

function fill_notification_badge(data) {
    var badges = document.getElementsByClassName(notify_badge_class);
    if (badges) {
        for (var i = 0; i < badges.length; i++) {
            badges[i].innerHTML = data.unread_count;
        }
    }
}

function fill_notification_list(data) {
    var menus = document.getElementsByClassName(notify_menu_class);
    if (menus) {
        var messages = data.unread_list
            .map(function (item) {
                var message = "";

                if (typeof item.actor !== "undefined") {
                    message = item.actor;
                }
                if (typeof item.verb !== "undefined") {
                    message = message + " " + item.verb;
                }
                if (typeof item.target !== "undefined") {
                    message = message + " " + item.target;
                }
                if (typeof item.timestamp !== "undefined") {
                    message = message + " " + item.timestamp;
                }
                return "<li>" + message + "</li>";
            })
            .join("");

        for (var i = 0; i < menus.length; i++) {
            menus[i].innerHTML = messages;
        }
    }
}

function register_notifier(func) {
    if (notify_state.registered_functions.indexOf(func) === -1) {
        notify_state.registered_functions.push(func);
    }
}

function schedule_next_fetch() {
    if (notify_state.poll_timer) {
        clearTimeout(notify_state.poll_timer);
    }

    if (notify_state.consecutive_misfires < 10) {
        notify_state.poll_timer = setTimeout(fetch_api_data, notify_refresh_period);
        window.__skylinxNotifyTimer = notify_state.poll_timer;
    } else {
        var badges = document.getElementsByClassName(notify_badge_class);
        if (badges) {
            for (var i = 0; i < badges.length; i++) {
                badges[i].innerHTML = "!";
                badges[i].title = "Connection lost!";
            }
        }
    }
}

function fetch_api_data() {
    if (notify_state.registered_functions.length > 0) {
        var r = new XMLHttpRequest();
        var params = "?max=" + notify_fetch_count;

        if (notify_mark_as_read) {
            params += "&mark_as_read=true";
        }

        r.addEventListener("readystatechange", function () {
            if (this.readyState === 4) {
                if (this.status === 200) {
                    notify_state.consecutive_misfires = 0;
                    try {
                        var data = JSON.parse(r.responseText);
                        for (var i = 0; i < notify_state.registered_functions.length; i++) {
                            notify_state.registered_functions[i](data);
                        }
                    } catch (error) {
                        notify_state.consecutive_misfires++;
                    }
                } else {
                    notify_state.consecutive_misfires++;
                }
            }
        });
        r.open("GET", notify_api_url + params, true);
        r.send();
    }

    schedule_next_fetch();
}

if (!window.__skylinxNotifyStarted) {
    window.__skylinxNotifyStarted = true;
    notify_state.started = true;
    sync_state();
    notify_state.poll_timer = setTimeout(fetch_api_data, 1000);
    window.__skylinxNotifyTimer = notify_state.poll_timer;
} else if (!notify_state.poll_timer && notify_state.registered_functions.length > 0) {
    notify_state.poll_timer = setTimeout(fetch_api_data, 1000);
    window.__skylinxNotifyTimer = notify_state.poll_timer;
}
