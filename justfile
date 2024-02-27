set dotenv-load := true

default: serve

serve:
    pdm run manage.py runserver 127.0.0.1:12111
