FROM python:3.10-alpine

RUN apk update && \
  apk add tzdata && \
  ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
  mkdir -p /opt/tmpant && \
  adduser -D tmpant && \
  chown tmpant:tmpant /opt/tmpant

WORKDIR /opt/tmpant
USER tmpant

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=tmpant:tmpant . .

CMD ["python", "tmp_annotations.py"]