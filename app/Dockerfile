FROM python:3.10-alpine

RUN apk update && \
  mkdir -p /opt/tmp_annotations && \
  adduser -D tmp_annotations && \
  chown tmp_annotations:tmp_annotations /opt/tmp_annotations

WORKDIR /opt/tmp_annotations
USER tmp_annotations

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=tmp_annotations:tmp_annotations . .

CMD ["python", "tmp_annotations.py"]