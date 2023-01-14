FROM pretix/standalone:stable
USER root
COPY --chown=pretixuser . /pretix-nowpayments
RUN export PYTHONPATH=$PYTHONPATH:/pretix/src && python -m pip install -e pretix-nowpayments
RUN export PYTHONPATH=$PYTHONPATH:/pretix/src && python -m pip install git+https://github.com/sausagenoods/NOWPayments-Python-API.git@send-api-key
USER pretixuser
RUN cd /pretix/src && make production
