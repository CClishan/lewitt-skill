// design-dna — page evaluation via CDP Runtime.evaluate.
// Avoids harness/string escaping layers entirely: the function source is sent as an expression.
module.exports = async function ddEvaluate(page, funcSrc, arg) {
  const cdp = await page.context().newCDPSession(page);
  try {
    const expr = arg === undefined
      ? `(${funcSrc})()`
      : `(${funcSrc})(${JSON.stringify(arg)})`;
    const r = await cdp.send('Runtime.evaluate', {
      expression: expr,
      returnByValue: true,
      awaitPromise: true,
      userGesture: true,
    });
    if (r.exceptionDetails) {
      const d = r.exceptionDetails;
      throw new Error((d.exception && (d.exception.description || d.exception.value)) || d.text);
    }
    return r.result.value;
  } finally {
    await cdp.detach().catch(() => {});
  }
};
