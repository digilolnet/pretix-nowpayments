FROM pretix/standalone:stable
USER root
COPY --chown=pretixuser . /pretix-nowpayments
RUN export PYTHONPATH=$PYTHONPATH:/pretix/src && python -m pip install -e pretix-nowpayments
USER pretixuser
RUN cd /pretix/src && make production
