export class OrderService {
  async syncAll(orders: Order[]): Promise<void> {
    for (const order of orders) {
      await this.orderRepository.save(order); // expect: io-or-query-in-loop
    }
  }

  async notifyAll(users: User[]) {
    for (const user of users) {
      await this.mailer.send(user); // expect: await-in-loop
    }
  }

  async parallel(users: User[]) {
    await Promise.all(
      users.map(async (user) => {
        await this.mailer.send(user);
      }),
    );
  }

  async inBatches(chunks: User[][]) {
    for (const chunk of chunks) {
      await this.userRepository.save(chunk);
    }
  }

  async paginate() {
    let cursor = null;
    while (true) {
      const page = await this.api.list(cursor);
      cursor = page.next;
      if (!cursor) break;
    }
  }

  async fetchEach(urls: string[]) {
    for (const url of urls) {
      const response = await fetch(url); // expect: io-or-query-in-loop
    }
  }

  async withOptions({
    orders,
    customers,
  }: {
    orders: Order[];
    customers: Customer[];
  }): Promise<void> {
    for (const order of orders) {
      const customer = customers.find((c) => c.id === order.customerId); // expect: nested-loop
    }
  }

  match(orders: Order[], customers: Customer[]) {
    return orders.map((order) => {
      const customer = customers.find((c) => c.id === order.customerId); // expect: nested-loop
      return { order, customer };
    });
  }

  withIndex(orders: Order[], customers: Customer[]) {
    const byId = new Map(customers.map((c) => [c.id, c]));
    return orders.map((order) => byId.get(order.customerId));
  }

  selected(items: Item[], ids: string[]) {
    return items.filter((item) => ids.includes(item.id)); // expect: membership-in-loop
  }

  setBacked(items: Item[], ids: Set<string>) {
    return items.filter((item) => ids.has(item.id));
  }

  ownTags(items: Item[], tag: string) {
    return items.filter((item) => item.tags.includes(tag));
  }

  lines(orders: Order[]) {
    let total = 0;
    for (const order of orders) {
      for (const line of order.lines) {
        total += line.amount;
      }
    }
    return total;
  }

  entries(groups: Record<string, Item[]>) {
    for (const [name, items] of Object.entries(groups)) {
      items.forEach((item) => console.log(name, item));
    }
  }

  byKey(items: Item[]) {
    return items.reduce((acc, item) => ({ ...acc, [item.id]: item }), {}); // expect: quadratic-accumulation
  }

  concatInLoop(pages: Item[][]) {
    let all: Item[] = [];
    for (const page of pages) {
      all = all.concat(page); // expect: quadratic-accumulation
    }
    return all;
  }

  pushInstead(items: Item[]) {
    return items.reduce((acc, item) => {
      acc.push(item.id);
      return acc;
    }, [] as string[]);
  }

  labels(items: Item[]) {
    const title = "for each item";
    return items.map((item) => `${item.name} for ${title}`);
  }

  multiLineTemplate(items: Item[]) {
    return items.map(
      (item) => `
        for every ${item.name} while we wait
      `,
    );
  }

  query() {
    return this.repo.find({ where: { active: true } });
  }

  drain(items: Item[]) {
    while (items.length) {
      const next = items.shift(); // expect: list-shift-in-loop
    }
  }

  clonePerItem(items: Item[], template: Template) {
    return items.map(() => JSON.parse(JSON.stringify(template))); // expect: deep-copy-in-loop
  }

  regexPerItem(lines: string[], word: string) {
    return lines.filter((line) => new RegExp(word).test(line)); // expect: regex-compile-in-loop
  }

  sortPerItem(groups: Group[], ranking: number[]) {
    for (const group of groups) {
      const top = ranking.sort((a, b) => b - a)[0]; // expect: sort-in-loop
    }
  }

  sortOwnItems(groups: Group[]) {
    for (const group of groups) {
      group.items.sort((a, b) => a.rank - b.rank);
    }
  }

  constantLookup(items: Item[]) {
    return items.filter((item) => SUPPORTED_TYPES.includes(item.type));
  }


  async firstReady(jobs: Job[]) {
    for (const job of jobs) {
      if (job.ready) return await this.runner.run(job);
    }
  }

  async pages() {
    for (let i = 0; i < this.maxPages; i++) {
      const page = await this.api.list({ offset: i * 100 });
    }
  }

  async withRetry(job: Job) {
    for (let attempt = 0; attempt < 3; attempt++) {
      await this.runner.run(job);
    }
  }

  chained(orders: Order[], customers: Customer[]) {
    for (const order of orders) {
      const matches = customers
        .filter((c) => c.region === order.region) // expect: nested-loop
        .map((c) => c.id);
    }
  }

  phases(clients: Client[], phaseByClient: Map<string, Phase>) {
    return clients.map((client) => phaseByClient.get(client.id));
  }

  async parallelQueries(ids: string[]) {
    return Promise.all(
      ids.map(async (id) => {
        return this.userRepository.findOne({ where: { id } }); // expect: io-or-query-in-loop
      }),
    );
  }
}
