const form = document.getElementById("job-form");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function pollJob(jobId) {
  while (true) {
    const response = await fetch(`/api/jobs/${jobId}`);
    const data = await response.json();
    statusEl.textContent = JSON.stringify(data, null, 2);

    if (data.status === "done") {
      resultEl.textContent = data.result || "任务完成，但没有文本输出";
      return;
    }

    if (data.status === "failed") {
      resultEl.textContent = `任务失败：${data.error || "未知错误"}`;
      return;
    }

    await sleep(1500);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultEl.textContent = "处理中，请稍候...";

  const payload = new FormData(form);
  const response = await fetch("/api/jobs", { method: "POST", body: payload });
  const data = await response.json();
  statusEl.textContent = JSON.stringify(data, null, 2);

  if (!data.job_id) {
    resultEl.textContent = `任务创建失败：${JSON.stringify(data)}`;
    return;
  }

  await pollJob(data.job_id);
});
