FROM nginx:alpine

LABEL org.opencontainers.image.source=https://github.com/Azure-Samples/swiss-llm-quickstart
LABEL org.opencontainers.image.description="Nginx ingress for Swiss LLM Quickstart"
LABEL org.opencontainers.image.licenses=MIT

COPY ./nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
