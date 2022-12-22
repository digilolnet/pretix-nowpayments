FROM pretix/standalone:stable
USER root
COPY . ./pretix_nowpayments
RUN cd ./pretix_nowpayments
RUN python setup.py develop
RUN make
USER pretixuser
RUN cd /pretix/src && make production
