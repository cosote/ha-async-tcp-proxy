ARG BUILD_FROM
FROM $BUILD_FROM

# Install python + pip
RUN \
  apk add --no-cache \
    python3 py3-pip

# Copy data for add-on
WORKDIR /
COPY run.sh /
COPY srv/async-tcp-proxy.py /

RUN chmod a+x /run.sh
CMD [ "/run.sh" ]