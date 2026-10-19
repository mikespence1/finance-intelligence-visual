# Publish On Vercel

The code changes are complete. Docker is not used. Uploaded datasets and chat history are now saved together in one PostgreSQL database. You do not need a separate file-storage service for the supported small uploads.

## 1. Push The Files

From the inner `finance-intelligence` folder:

```powershell
$env:Path = "C:\Program Files\Git\cmd;$env:Path"
git add .
git status
git commit -m "Prepare Vercel deployment with shared workspace storage"
git push origin main
```

Check that `secrets.toml`, `.venv`, `node_modules` and `.local` are not listed for commit. New Vercel configuration, the storage module and Docker-file deletions should be listed.

## 2. Import Your Project

In Vercel, choose **Add New → Project**, import your GitHub repository, and use:

| Setting | Value |
| --- | --- |
| Root Directory | `finance-intelligence` (the inner project folder) |
| Framework Preset | FastAPI |
| Build Command | Automatically read from `vercel.json` |
| Install Command | Framework default |
| Output Directory | Framework default |

The configured build command is `npm ci --include=dev && npm run build`. The Python entrypoint is already configured as `backend.main:app`. Python is pinned to 3.12. You do not need a Dockerfile, a separate frontend project, or a custom start command.

You can create the project before connecting the database. If the initial deployment opens but the dashboard reports that workspace storage is unavailable, complete the next step.

## 3. Connect The Database — No Database Coding Required

1. Open your Vercel project.
2. Open **Storage** and choose **Create Database** or the storage Marketplace link.
3. Choose **Neon**, a PostgreSQL provider, and follow its account/plan prompts. Review the provider's plan before confirming.
4. Create a database in a suitable region and connect it to this Vercel project.
5. Select the deployment environments you need. Use separate Neon preview branches/databases when available rather than mixing preview and production company data.
6. Open **Settings → Environment Variables**. Confirm that a variable named **`DATABASE_URL`** was added for Production (and Preview if needed).

`DATABASE_URL` is the complete PostgreSQL connection string, not the database's website address. Prefer the pooled connection string provided by Neon and retain its SSL parameters. If the integration added a prefixed variable instead, add `DATABASE_URL` with the same pooled connection-string value. Keep this value private; do not paste it in chat or into React source.

The app creates its `finance_workspaces` table automatically on first storage access. You do not need to run SQL, create tables manually, or copy your local SQLite database to Vercel. Local uploads are not automatically migrated; upload those source files again in the hosted website.

## 4. Set Demo Environment Variables

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Added by the Neon integration |
| `COOKIE_SECURE` | `1` |
| `AI_DISABLED` | `1` |

Keep **Enable access to System Environment Variables** enabled. The app recognises its Vercel production and deployment URLs automatically. For a custom frontend origin that is not recognised, set `APP_ORIGIN=https://your-domain.example` without a trailing slash.

AI is disabled by default on Vercel unless you explicitly set `AI_DISABLED=0`. Once the site has suitable access control, enable it and add `OPENAI_API_KEY` and optionally `OPENAI_MODEL`. Use a new key rather than any key previously disclosed in chat. Never deploy `.streamlit/secrets.toml`; it is excluded from both source upload and the Python function bundle.

## 5. Redeploy And Check

After connecting the database or changing environment variables, open **Deployments** and redeploy the latest commit.

Visit `/api/health` on the deployment URL. It should return `{"status":"ok"}` once storage is configured. Then check the dashboard, filters, uploads and all three board-pack downloads. Refresh after uploading: the loaded data should remain. AI reports and chat will report that AI is disabled for this demo.

Workspaces survive function-instance changes and backend restarts. They still expire after two hours without activity and are tied to that browser's cookie, not to a user account. Closing/reopening a tab is supported while the cookie remains valid. Another browser gets a separate workspace.

## Upload Limits

Each source file must be at most **1 MB**. Three files are sent together; the app caps requests and generated responses at **4 MB** to stay below Vercel's 4.5 MB function limit. For larger production datasets, direct-to-object-storage uploads and background report jobs would be a separate extension.

## If Something Does Not Work

| Message | Action |
| --- | --- |
| Workspace storage is unavailable | Check Neon is connected, `DATABASE_URL` is set for the current environment, and redeploy |
| Origin not permitted | Enable system environment variables or set `APP_ORIGIN` to the exact website origin |
| Workspace expired | Refresh, then load sample data or upload the three files again |
| Workspace changed in another request | Refresh; another tab/request updated the same workspace |
| Upload or output exceeds the size limit | Reduce the input files/reporting dataset |

Official references: [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [Neon integration](https://neon.com/docs/guides/vercel-managed-integration), [Vercel function limits](https://vercel.com/docs/functions/limitations).
