/**
 * AudioWorkletProcessor: downsamples mic audio from the AudioContext sample
 * rate (typically 48 kHz) to 16 kHz using a box filter (averaging), then
 * posts Int16Array chunks to the main thread for WebSocket transmission.
 *
 * Running in the AudioWorklet thread means audio processing never competes
 * with the main thread and render quanta arrive with consistent timing.
 */
class PcmDownsamplerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // sampleRate is a global in AudioWorkletGlobalScope
    this._ratio      = sampleRate / 16000;
    this._outChunk   = 1365;                           // output samples per chunk (~85 ms)
    this._inChunk    = Math.round(this._outChunk * this._ratio); // input samples needed
    this._pending    = [];
    this._pendingLen = 0;
  }

  process(inputs) {
    const ch = inputs[0]?.[0];
    if (!ch || ch.length === 0) return true;

    this._pending.push(ch.slice());
    this._pendingLen += ch.length;

    while (this._pendingLen >= this._inChunk) {
      // Flatten buffered render quanta into one contiguous array
      const flat = new Float32Array(this._pendingLen);
      let off = 0;
      for (const buf of this._pending) { flat.set(buf, off); off += buf.length; }

      // Box-filter downsample: average all input samples that map to each output sample
      const out = new Int16Array(this._outChunk);
      for (let i = 0; i < this._outChunk; i++) {
        const start = Math.floor(i * this._ratio);
        const end   = Math.floor((i + 1) * this._ratio);
        let sum = 0;
        for (let j = start; j < end; j++) sum += flat[j];
        out[i] = Math.max(-32768, Math.min(32767, (sum / (end - start)) * 32768));
      }

      // Transfer buffer ownership (zero-copy) to main thread
      this.port.postMessage(out.buffer, [out.buffer]);

      // Keep samples beyond this chunk for the next iteration
      const remainder = flat.slice(this._inChunk);
      this._pending    = remainder.length ? [remainder] : [];
      this._pendingLen = remainder.length;
    }

    return true; // keep processor alive
  }
}

registerProcessor('pcm-downsampler', PcmDownsamplerProcessor);
