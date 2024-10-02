ARG BUILD_FROM
FROM $BUILD_FROM

# Install python + pip
RUN apk add --no-cache python3 py3-pip py3-pysocks

# Install python modules
#RUN pip install PySocks

# Copy data for add-on
WORKDIR /
COPY run.sh /
COPY src/ /

RUN chmod a+x /run.sh
CMD [ "/run.sh" ]
