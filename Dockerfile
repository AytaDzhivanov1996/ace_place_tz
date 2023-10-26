FROM python:3.11.6

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

ENV PORT 5000

EXPOSE 5000

ENTRYPOINT [ "python" ]

CMD [ "main.py" ]

