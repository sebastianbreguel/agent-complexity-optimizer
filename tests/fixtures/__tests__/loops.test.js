test("pairs", () => {
  for (const a of listA) {
    for (const b of listB) {
      expect(a).not.toBe(b);
    }
  }
});
