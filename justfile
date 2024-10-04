set dotenv-load := true

default: serve

serve:
    #!/bin/bash
    export DJANGO_DEBUG=1
    pdm run manage.py runserver 127.0.0.1:12111
