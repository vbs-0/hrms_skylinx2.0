import os

filepath = 'skylinx/settings/base.py'
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'LOGGING =' not in content:
        logging_config = '''

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'skylinx_audit.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'skylinx': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
'''
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(logging_config)
        print("Logging config appended.")
    else:
        print("Logging already configured.")
