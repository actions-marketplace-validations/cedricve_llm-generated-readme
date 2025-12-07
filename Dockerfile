FROM python:3.13.5-bullseye

RUN apt-get update
RUN apt-get -y install jq
COPY entrypoint.sh /action/entrypoint.sh
COPY autofill_readme.py /action/autofill_readme.py
COPY requirements.txt /action/requirements.txt
RUN pip3 install -r /action/requirements.txt
RUN chmod +x /action/entrypoint.sh
RUN chmod +x /action/autofill_readme.py

ENTRYPOINT ["/action/entrypoint.sh"]
