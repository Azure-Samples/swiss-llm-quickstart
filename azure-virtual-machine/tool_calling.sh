#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

# Example: call the local OpenAI-compatible chat completion API and demonstrate function/tool calling.
API_URL="http://localhost:8000/v1/chat/completions"
MODEL="swiss-ai/Apertus-8B-Instruct-2509"

# ensure jq is available for JSON parsing
command -v jq >/dev/null 2>&1 || { echo "jq is required. Install with: sudo apt-get install -y jq" >&2; exit 1; }

# Build initial request with a single tool: get_current_weather
PAYLOAD1=$(cat <<JSON
{
  "model": "${MODEL}",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather in Paris?"}
  ],
  "tools": [
    {
      "type": "function",
        "description": "Get the current weather in a given city",
        "name": "get_current_weather",
      "function": {
        "name": "get_current_weather",
        "parameters": {
          "type": "object",
          "properties": {
            "city": { "type": "string", "description": "Name of the city, e.g. Paris" }
          },
          "required": ["city"]
        }
      }
    }
  ]
}
JSON
)

# 1) ask the model what to do (it may decide to call our function)
resp1=$(curl -sS "$API_URL" -H "Content-Type: application/json" -d "$PAYLOAD1")

echo $resp1 | jq .

# check if model requested a function call
fn_name=$(echo "$resp1" | jq -r '.choices[0].message.function_call.name // empty')
fn_args_raw=$(echo "$resp1" | jq -r '.choices[0].message.function_call.arguments // empty')

if [ -z "$fn_name" ]; then
  # no tool call requested — just print assistant content
  echo "Assistant response (no function call):"
  echo "$resp1" | jq -r '.choices[0].message.content'
  exit 0
fi

# parse the function arguments (the API often returns them as a JSON-encoded string)
city=$(printf '%s' "$fn_args_raw" | jq -r 'try fromjson.city // .city // empty')
unit=$(printf '%s' "$fn_args_raw" | jq -r 'try fromjson.unit // .unit // "metric"')

# Simple tool implementation: get_current_weather
# This tries to use wttr.in to fetch real weather JSON; if unavailable it returns a mock result.
perform_get_current_weather() {
  local city="$1" unit="$2"
  # be resilient for spaces in city names
  local city_enc
  city_enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$city" 2>/dev/null) || city_enc=$(echo "$city" | sed 's/ /%20/g')

  if curl -sS "https://wttr.in/${city_enc}?format=j1" -m 10 -o /tmp/wttr.json 2>/dev/null; then
    temp_c=$(jq -r '.current_condition[0].temp_C' /tmp/wttr.json)
    temp_f=$(jq -r '.current_condition[0].temp_F' /tmp/wttr.json)
    desc=$(jq -r '.current_condition[0].weatherDesc[0].value' /tmp/wttr.json)
    if [ "$unit" = "imperial" ]; then
      temp="$temp_f"
      unit_label="F"
    else
      temp="$temp_c"
      unit_label="C"
    fi
    jq -n --arg location "$city" --arg temperature "$temp" --arg unit "$unit_label" --arg description "$desc" 
      '{location:$location,temperature:$temperature,unit:$unit,description:$description}'
  else
    # fallback mock response
    jq -n --arg location "$city" --arg temperature "20" --arg unit "C" --arg description "Partly cloudy" 
      '{location:$location,temperature:$temperature,unit:$unit,description:$description}'
  fi
}

# call the tool and capture a compact JSON result
tool_result_json=$(perform_get_current_weather "$city" "$unit" | jq -c .)
# escape the JSON so it can be safely inserted as a string value in the next payload
tool_result_escaped=$(printf '%s' "$tool_result_json" | jq -R -s .)

# 2) send the tool result back to the model as a function message and ask for the final assistant response
PAYLOAD2=$(cat <<JSON
{
  "model": "${MODEL}",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather in Paris?"},
    {"role": "function", "name": "${fn_name}", "content": $tool_result_escaped}
  ]
}
JSON
)

resp2=$(curl -sS "$API_URL" -H "Content-Type: application/json" -d "$PAYLOAD2")

# print the final assistant reply
echo "Final assistant response:"
echo "$resp2" | jq -r '.choices[0].message.content // .choices[0].message'