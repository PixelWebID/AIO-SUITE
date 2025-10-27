
const fs = require('fs/promises');
const { randomUUID } = require('crypto');

const TICK_INTERVAL = 1000 * 30; // 30 seconds

class Scheduler {
  constructor(storagePath, deliverFn) {
    this.storagePath = storagePath;
    this.deliverFn = deliverFn;
    this.queue = new Map();
    this.history = [];
    this.timer = null;
  }

  async init() {
    try {
      const file = await fs.readFile(this.storagePath, 'utf8');
      const records = JSON.parse(file);
      records.forEach((record) => {
        if (record.status === 'scheduled') {
          this._register(record);
        } else {
          this.history.push(record);
        }
      });
    } catch (error) {
      await fs.writeFile(this.storagePath, '[]', 'utf8');
    }

    if (!this.timer) {
      this.timer = setInterval(() => this._tick(), TICK_INTERVAL);
    }
  }

  listScheduled() {
    return Array.from(this.queue.values()).map((item) => ({ ...item }));
  }

  listHistory(limit = 20) {
    return this.history.slice(-limit).reverse();
  }

  async recordImmediate(payload, result) {
    const record = {
      id: randomUUID(),
      status: result?.deliveries ? 'sent' : 'failed',
      deliveredAt: new Date().toISOString(),
      payload,
      result,
    };
    this.history.push(record);
    await this._persist();
    return record;
  }

  async schedule(job) {
    const record = {
      ...job,
      id: job.id || randomUUID(),
      status: 'scheduled',
      createdAt: job.createdAt || new Date().toISOString(),
    };

    if (new Date(record.runAt).getTime() <= Date.now()) {
      return this._execute(record);
    }

    this._register(record);
    await this._persist();
    return record;
  }

  async _tick() {
    const now = Date.now();
    for (const record of this.queue.values()) {
      if (new Date(record.runAt).getTime() <= now) {
        await this._execute(record);
      }
    }
  }

  _register(record) {
    this.queue.set(record.id, record);
  }

  async _execute(record) {
    this.queue.delete(record.id);
    try {
      const result = await this.deliverFn(record.payload, { immediate: true });
      const historyRecord = {
        ...record,
        status: 'sent',
        deliveredAt: new Date().toISOString(),
        result,
      };
      this.history.push(historyRecord);
      await this._persist();
      return historyRecord;
    } catch (error) {
      const failureRecord = {
        ...record,
        status: 'failed',
        deliveredAt: new Date().toISOString(),
        error: error.message,
      };
      this.history.push(failureRecord);
      await this._persist();
      return failureRecord;
    }
  }

  async _persist() {
    const payload = [...this.queue.values(), ...this.history];
    await fs.writeFile(this.storagePath, JSON.stringify(payload, null, 2), 'utf8');
  }
}

module.exports = { Scheduler };

