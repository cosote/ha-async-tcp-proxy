ARG BUILD_FROM
FROM $BUILD_FROM

# Install python + pip
RUN apk add --no-cache python3 py3-pip

# Install python modules
RUN pip install PySocks

# Copy data for add-on
WORKDIR /
COPY run.sh /
COPY src/async-tcp-proxy.py /
COPY src/proxymodules/hexdump.py /proxymodules/

RUN chmod a+x /run.sh
CMD [ "/run.sh" ]