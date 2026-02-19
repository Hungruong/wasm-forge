import { mockModels, mockPlugins, mockRunResult } from "./mock";

const USE_MOCK = false; // ← backend is ready
const API_URL = "http://172.234.27.110:8000"; 

export async function getModels() {
  if (USE_MOCK) return mockModels;
  const res = await fetch(`${API_URL}/api/models/list`);
  return await res.json(); // returns array directly
}

export async function getPlugins() {
  if (USE_MOCK) return mockPlugins;
  const res = await fetch(`${API_URL}/api/plugins/list`);
  return await res.json(); // returns array directly
}

export async function getPluginCode(pluginName) {
  if (USE_MOCK) return "";
  const res = await fetch(`${API_URL}/api/plugins/${pluginName}/code`);
  const data = await res.json();
  return data.code;
}

export async function uploadPlugin(name, code, metadata = {}) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800));
    return { status: "uploaded" };
  }
  const blob = new Blob([code], { type: "text/plain" });
  const formData = new FormData();
  formData.append("file", blob, name.endsWith(".py") ? name : name + ".py");
  formData.append("description", metadata.description || "");
  formData.append("input_type", metadata.input_type || "text");
  formData.append("input_hint", metadata.input_hint || "");
  const res = await fetch(`${API_URL}/api/plugins/upload`, {
    method: "POST",
    body: formData,
  });
  return await res.json();
}

export async function deletePlugin(pluginName) {
  if (USE_MOCK) return true;
  const res = await fetch(`${API_URL}/api/plugins/${pluginName}`, {
    method: "DELETE",
  });
  return res.ok;
}

export async function runPlugin(pluginName, inputData) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 2200));

    if (inputData && inputData.startsWith("data:image")) {
      return {
        status: "success",
        result:
          "The image shows a landscape with mountains in the background and a river flowing through a green valley.",
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
            summary: "JSON input processed successfully.",
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
  const data = await res.json();

  // Map backend response to frontend format
  return {
    status: data.success ? "success" : "error",
    result: data.output || "",
    error: data.error || null,
    error_type: data.error_type || null,
  };
}