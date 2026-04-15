module.exports = {
  timeout: 30000,
  expect: {
    timeout: 10000,
  },
  use: {
    channel: "chrome",
    viewport: { width: 1440, height: 1000 },
    ignoreHTTPSErrors: true,
    trace: "off",
  },
  reporter: [["list"]],
};
