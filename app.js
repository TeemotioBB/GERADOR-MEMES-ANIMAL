(() => {
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  const body = document.body;
  const maxBatchSize = Number(body.dataset.maxBatchSize || 50);
  const elements = {
    imageInput: $('#imageInput'),
    format: $('#formatSelect'),
    fitMode: $('#fitMode'),
    model: $('#modelInput'),
    apiKey: $('#apiKeyInput'),
    count: $('#countInput'),
    intensity: $('#intensitySelect'),
    duration: $('#durationInput'),
    theme: $('#themeInput'),
    tone: $('#toneInput'),
    examples: $('#examplesInput'),
    prompt: $('#promptInput'),
    textTop: $('#textTop'),
    textHeight: $('#textHeight'),
    textMargin: $('#textMargin'),
    fontMax: $('#fontMax'),
    lineSpacing: $('#lineSpacing'),
    watermarkSize: $('#watermarkSize'),
    watermark: $('#watermarkInput'),
    textColor: $('#textColor'),
    previewFrame: $('#previewFrame'),
    previewImage: $('#previewImage'),
    previewText: $('#previewText'),
    previewWatermark: $('#previewWatermark'),
    phraseList: $('#phraseList'),
    generate: $('#generateButton'),
    addPhrase: $('#addPhraseButton'),
    exactPreview: $('#serverPreviewButton'),
    batch: $('#batchButton'),
    download: $('#downloadButton'),
    jobArea: $('#jobArea'),
    jobMessage: $('#jobMessage'),
    jobCounter: $('#jobCounter'),
    jobError: $('#jobError'),
    progressBar: $('#progressBar'),
    toast: $('#toast'),
  };

  let localImageUrl = null;
  let exactPreviewUrl = null;
  let toastTimer = null;

  function showToast(message, isError = false) {
    clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.remove('hidden', 'error');
    if (isError) elements.toast.classList.add('error');
    toastTimer = setTimeout(() => elements.toast.classList.add('hidden'), 5000);
  }

  function extractError(payload, fallback = 'Ocorreu um erro.') {
    if (!payload) return fallback;
    if (typeof payload.detail === 'string') return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg || JSON.stringify(item)).join(' | ');
    }
    return payload.message || fallback;
  }

  function dimensions() {
    const [width, height] = elements.format.value.split('x').map(Number);
    return { width, height };
  }

  function renderSettings() {
    const { width, height } = dimensions();
    return {
      width,
      height,
      fit_mode: elements.fitMode.value,
      text_top_pct: Number(elements.textTop.value),
      text_height_pct: Number(elements.textHeight.value),
      text_margin_pct: Number(elements.textMargin.value),
      font_max: Number(elements.fontMax.value),
      font_min: Math.max(20, Math.min(38, Number(elements.fontMax.value) - 2)),
      line_spacing: Number(elements.lineSpacing.value),
      text_color: elements.textColor.value,
      watermark: elements.watermark.value,
      watermark_x_pct: 7.5,
      watermark_y_pct: 84,
      watermark_size: Number(elements.watermarkSize.value),
      watermark_color: '#111111',
      video_duration: Number(elements.duration.value),
      jpeg_quality: 95,
    };
  }

  function updateSliderOutputs() {
    $('#textTopOutput').value = `${String(elements.textTop.value).replace('.', ',')}%`;
    $('#textHeightOutput').value = `${String(elements.textHeight.value).replace('.', ',')}%`;
    $('#textMarginOutput').value = `${String(elements.textMargin.value).replace('.', ',')}%`;
    $('#fontMaxOutput').value = `${elements.fontMax.value}px`;
    $('#lineSpacingOutput').value = String(elements.lineSpacing.value).replace('.', ',');
    $('#watermarkSizeOutput').value = `${elements.watermarkSize.value}px`;
  }

  function firstPhrase() {
    return $('.phrase-row textarea')?.value.trim() || 'Sua frase aparece aqui.';
  }

  function updateBrowserPreview() {
    const { width, height } = dimensions();
    elements.previewFrame.classList.remove('ratio-9-16', 'ratio-4-5', 'ratio-1-1');
    if (width / height === 1) elements.previewFrame.classList.add('ratio-1-1');
    else if (Math.abs(width / height - 0.8) < 0.01) elements.previewFrame.classList.add('ratio-4-5');
    else elements.previewFrame.classList.add('ratio-9-16');

    elements.previewImage.style.objectFit = elements.fitMode.value === 'stretch' ? 'fill' : elements.fitMode.value;
    elements.previewText.textContent = firstPhrase();
    elements.previewText.style.top = `${elements.textTop.value}%`;
    elements.previewText.style.height = `${elements.textHeight.value}%`;
    elements.previewText.style.left = `${elements.textMargin.value}%`;
    elements.previewText.style.right = `${elements.textMargin.value}%`;
    elements.previewText.style.lineHeight = elements.lineSpacing.value;
    elements.previewText.style.color = elements.textColor.value;
    elements.previewWatermark.textContent = elements.watermark.value;

    const relativeFont = Number(elements.fontMax.value) / 1080;
    elements.previewText.style.fontSize = `${Math.max(17, relativeFont * elements.previewFrame.clientWidth)}px`;
    elements.previewWatermark.style.fontSize = `${Math.max(11, (Number(elements.watermarkSize.value) / 1080) * elements.previewFrame.clientWidth)}px`;
  }

  function renumberPhrases() {
    $$('.phrase-row').forEach((row, index) => {
      row.querySelector('.phrase-number').textContent = index + 1;
    });
    updateBrowserPreview();
  }

  function phraseRow(value = '') {
    const row = document.createElement('div');
    row.className = 'phrase-row';
    row.innerHTML = `
      <span class="phrase-number"></span>
      <textarea rows="3"></textarea>
      <button class="delete-phrase" title="Excluir frase">×</button>
    `;
    row.querySelector('textarea').value = value;
    row.querySelector('textarea').addEventListener('input', updateBrowserPreview);
    row.querySelector('.delete-phrase').addEventListener('click', () => {
      row.remove();
      if (!$('.phrase-row')) elements.phraseList.appendChild(phraseRow(''));
      renumberPhrases();
    });
    return row;
  }

  function replacePhrases(phrases) {
    elements.phraseList.innerHTML = '';
    phrases.forEach((phrase) => elements.phraseList.appendChild(phraseRow(phrase)));
    renumberPhrases();
  }

  function collectPhrases() {
    return $$('.phrase-row textarea')
      .map((textarea) => textarea.value.trim())
      .filter(Boolean);
  }

  async function generatePhrases() {
    const count = Math.max(1, Math.min(Number(elements.count.value), maxBatchSize));
    elements.generate.disabled = true;
    elements.generate.textContent = 'Gerando frases...';

    try {
      const response = await fetch('/api/phrases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          count,
          theme: elements.theme.value,
          tone: elements.tone.value,
          intensity: elements.intensity.value,
          examples: elements.examples.value,
          prompt: elements.prompt.value,
          model: elements.model.value,
          api_key: elements.apiKey.value,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(extractError(payload, 'Não foi possível gerar as frases.'));
      replacePhrases(payload.phrases || []);
      showToast(`${payload.phrases.length} frases geradas com ${payload.model}.`);
    } catch (error) {
      showToast(error.message, true);
    } finally {
      elements.generate.disabled = false;
      elements.generate.innerHTML = '<span class="button-icon">✦</span> Gerar frases com IA';
    }
  }

  function appendImageToForm(formData) {
    const file = elements.imageInput.files?.[0];
    if (file) formData.append('image', file);
  }

  async function renderExactPreview() {
    const phrase = firstPhrase();
    if (!phrase) return showToast('Adicione uma frase para gerar a prévia.', true);

    elements.exactPreview.disabled = true;
    elements.exactPreview.textContent = 'Renderizando...';
    try {
      const formData = new FormData();
      formData.append('phrase', phrase);
      formData.append('settings_json', JSON.stringify(renderSettings()));
      appendImageToForm(formData);

      const response = await fetch('/api/preview', { method: 'POST', body: formData });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(extractError(payload, 'Falha ao gerar a prévia.'));
      }
      const blob = await response.blob();
      if (exactPreviewUrl) URL.revokeObjectURL(exactPreviewUrl);
      exactPreviewUrl = URL.createObjectURL(blob);
      elements.previewImage.src = exactPreviewUrl;
      elements.previewText.style.display = 'none';
      elements.previewWatermark.style.display = 'none';
      showToast('Prévia exata gerada pelo servidor.');
    } catch (error) {
      showToast(error.message, true);
    } finally {
      elements.exactPreview.disabled = false;
      elements.exactPreview.textContent = 'Gerar prévia exata';
    }
  }

  function restoreOverlayPreview() {
    elements.previewText.style.display = 'flex';
    elements.previewWatermark.style.display = 'block';
    if (localImageUrl) elements.previewImage.src = localImageUrl;
    else elements.previewImage.src = '/sample-dog.jpg';
    updateBrowserPreview();
  }

  async function startBatch() {
    const phrases = collectPhrases();
    if (!phrases.length) return showToast('Adicione ao menos uma frase.', true);
    if (phrases.length > maxBatchSize) return showToast(`O máximo por lote é ${maxBatchSize}.`, true);

    elements.batch.disabled = true;
    elements.download.classList.add('hidden');
    elements.jobArea.classList.remove('hidden');
    elements.jobError.classList.add('hidden');
    elements.progressBar.style.width = '0%';
    elements.jobMessage.textContent = 'Enviando lote...';
    elements.jobCounter.textContent = `0/${phrases.length}`;

    try {
      const formData = new FormData();
      formData.append('phrases_json', JSON.stringify(phrases));
      formData.append('settings_json', JSON.stringify(renderSettings()));
      appendImageToForm(formData);

      const response = await fetch('/api/jobs', { method: 'POST', body: formData });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(extractError(payload, 'Não foi possível iniciar o lote.'));
      await pollJob(payload.job_id);
    } catch (error) {
      elements.jobMessage.textContent = 'Falha';
      elements.jobError.textContent = error.message;
      elements.jobError.classList.remove('hidden');
      elements.batch.disabled = false;
      showToast(error.message, true);
    }
  }

  async function pollJob(jobId) {
    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const response = await fetch(`/api/jobs/${jobId}`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(extractError(payload, 'Não foi possível acompanhar o lote.'));

      const progress = Number(payload.progress || 0);
      const total = Number(payload.total || 1);
      const percentage = Math.max(0, Math.min(100, (progress / total) * 100));
      elements.jobMessage.textContent = payload.message || payload.status;
      elements.jobCounter.textContent = `${progress}/${total}`;
      elements.progressBar.style.width = `${percentage}%`;

      if (payload.status === 'completed') {
        elements.batch.disabled = false;
        elements.download.href = `/api/jobs/${jobId}/download`;
        elements.download.classList.remove('hidden');
        showToast('Lote pronto para baixar.');
        return;
      }
      if (payload.status === 'failed') {
        elements.batch.disabled = false;
        elements.jobError.textContent = payload.error || 'Falha desconhecida.';
        elements.jobError.classList.remove('hidden');
        throw new Error(payload.error || 'Falha ao gerar o lote.');
      }
    }
  }

  elements.imageInput.addEventListener('change', () => {
    if (localImageUrl) URL.revokeObjectURL(localImageUrl);
    const file = elements.imageInput.files?.[0];
    localImageUrl = file ? URL.createObjectURL(file) : null;
    restoreOverlayPreview();
  });

  elements.generate.addEventListener('click', generatePhrases);
  elements.exactPreview.addEventListener('click', renderExactPreview);
  elements.batch.addEventListener('click', startBatch);
  elements.addPhrase.addEventListener('click', () => {
    elements.phraseList.appendChild(phraseRow(''));
    renumberPhrases();
    elements.phraseList.lastElementChild.querySelector('textarea').focus();
  });

  $$('.delete-phrase').forEach((button) => {
    button.addEventListener('click', () => {
      button.closest('.phrase-row').remove();
      if (!$('.phrase-row')) elements.phraseList.appendChild(phraseRow(''));
      renumberPhrases();
    });
  });
  $$('.phrase-row textarea').forEach((textarea) => textarea.addEventListener('input', updateBrowserPreview));

  [
    elements.format, elements.fitMode, elements.textTop, elements.textHeight,
    elements.textMargin, elements.fontMax, elements.lineSpacing, elements.watermarkSize,
    elements.watermark, elements.textColor,
  ].forEach((control) => {
    control.addEventListener('input', () => {
      updateSliderOutputs();
      restoreOverlayPreview();
    });
    control.addEventListener('change', () => {
      updateSliderOutputs();
      restoreOverlayPreview();
    });
  });

  window.addEventListener('resize', updateBrowserPreview);
  updateSliderOutputs();
  updateBrowserPreview();
})();
