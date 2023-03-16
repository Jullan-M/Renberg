FROM python:3.8
COPY *.py ./
COPY .env ./
COPY config/ config/
COPY embeds/ embeds/
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "-u", "./run_bot.py"]