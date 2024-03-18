ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY requirements.txt /usr/src/
RUN \
    pip3 install \
        -r /usr/src/requirements.txt \
    && rm -f /usr/src/requirements.txt

COPY dvr-alarm-server.py /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]