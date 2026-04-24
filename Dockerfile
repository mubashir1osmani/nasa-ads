FROM python:3.11-slim

RUN pip install uv

COPY dist/*.whl /tmp/
RUN uv pip install --system /tmp/nasa_ads_mcp-*.whl

ENV NASA_ADS_MCP_HOST=0.0.0.0
ENV NASA_ADS_MCP_PORT=8766
ENV NASA_ADS_MCP_TRANSPORT=streamable-http

EXPOSE 8766

ENTRYPOINT ["nasa-ads-mcp"]