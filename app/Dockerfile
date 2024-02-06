FROM python:3.10-alpine

RUN apk update && \
  apk add tzdata && \
  ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
  mkdir -p /opt/tmpant && \
  adduser -D tmpant && \
  chown tmpant:tmpant /opt/tmpant

WORKDIR /opt/tmpant
USER tmpant

COPY --chown=tmpant:tmpant requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=tmpant:tmpant . .
ENV PATH $PATH:/home/tmpant/.local/bin

CMD [ "gunicorn", "tmp_annotations:app" ]