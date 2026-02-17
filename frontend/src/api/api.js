import { mockModels, mockPlugins, mockRunResult } from "./mock";

const USE_MOCK = true; // ← set false when backend is ready
const API_URL = "http://172.237.150.80:8000";

export async function getModels() {
  if (USE_MOCK) return mockModels;
  const res = await fetch(`${API_URL}/api/models/list`);
  const data = await res.json();
  return data.models;
}

export async function getPlugins() {
  if (USE_MOCK) return mockPlugins;
  const res = await fetch(`${API_URL}/api/plugins/list`);
  const data = await res.json();
  return data.plugins;
}

export async function uploadPlugin(name, code, metadata = {}) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800));
    return { status: "uploaded" };
  }
  const blob = new Blob([code], { type: "text/plain" });
  const formData = new FormData();
  formData.append("file", blob, name + ".py");
  formData.append("description", metadata.description || "");
  formData.append("input_type", metadata.input_type || "text");
  formData.append("input_hint", metadata.input_hint || "");
  const res = await fetch(`${API_URL}/api/plugins/upload`, {
    method: "POST",
    body: formData,
  });
  return await res.json();
}

export async function runPlugin(pluginName, inputData) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 2200));

    if (inputData && inputData.startsWith("data:image")) {
      return {
        status: "success",
        result:
          "The image shows a landscape with mountains in the background and a river flowing through a green valley. The sky is partly cloudy with warm sunlight breaking through.",
      };
    }

    try {
      JSON.parse(inputData);
      return {
        status: "success",
        result: JSON.stringify(
          {
            processed: true,
            input_keys: Object.keys(JSON.parse(inputData)),
            summary: "JSON input processed successfully. All fields validated and analyzed.",
          },
          null,
          2
        ),
      };
    } catch {}

    return mockRunResult;
  }

  const formData = new FormData();
  formData.append("plugin_name", pluginName);
  formData.append("input_data", inputData);
  const res = await fetch(`${API_URL}/api/plugins/run`, {
    method: "POST",
    body: formData,
  });
  return await res.json();
}