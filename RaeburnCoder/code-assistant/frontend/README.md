# Code Assistant Frontend

This React + Vite app provides a Monaco-based code editor with inline AI actions and a prompt panel for chatting with the model.

## Setup

1. Install dependencies
   ```bash
   npm install
   ```
2. Start the development server
   ```bash
   npm run dev
   ```

The app expects the backend running on `localhost:3001` and proxies `/api` requests to it.

The prompt panel below the editor lets you select a predefined role (e.g. Rust expert) and run code improvement tools such as explaining the file, improving performance, adding documentation or generating tests. You can also type custom prompts and view the model and token usage for each response.

### Testing

Run unit tests with:

```bash
npm test
```
