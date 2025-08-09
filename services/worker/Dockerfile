FROM python:3.11-slim

COPY ./services/worker/ .
RUN pip install -r requirements.txt

CMD ["python", "worker.py"]
