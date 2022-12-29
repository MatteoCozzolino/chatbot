FROM rasa/rasa:3.3.3-full

USER root
RUN pip install -U pip setuptools wheel
RUN pip install -U spacy
RUN python -m spacy download it_core_news_md

USER 1001