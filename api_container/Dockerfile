FROM python:3.10.12 
WORKDIR /code/

COPY ./api_container/ /code/
COPY ./lib/ /code/lib/

RUN cat /code/lib/requirements.txt >> /code/requirements.txt

COPY ./api_container/.env /code/.env
RUN cat ./lib/.env >> /code/.env

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

CMD ["uvicorn", "support_api:app", "--port", "9212", "--host", "0.0.0.0", "--reload"]
