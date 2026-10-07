# REPORT

## Hardware/Software
Python: 3.14.6 on Linux 7.1.10-200.fc44.x86_64 (x86_64)
CPU: AMD Ryzen 7 8845HS w/ Radeon 780M Graphics
nvidia-smi: no

## Models
- Target agent model id: itmo-agent (from Modelfile.agent)
- Experiment model id: itmo-experiment (from Modelfile)

Installed (Ollama):
- itmo-agent:latest quant=None context=262144
- itmo-experiment:latest quant=None context=262144
- qwen3.5:4b quant=None context=262144

## Modelfiles
### Modelfile.agent
```
FROM qwen3.5:4b
PARAMETER num_ctx 65536
PARAMETER temperature 0.2
```

### Modelfile
```
FROM qwen3.5:4b
PARAMETER num_ctx 4096
PARAMETER temperature 0.2
SYSTEM """Ты помощник по учебному проекту. Отвечай по предоставленным фактам.
Если данных нет, напиши «В предоставленных материалах нет ответа».
Не выдумывай файлы и настройки. Дай короткий ответ и основание."""
```