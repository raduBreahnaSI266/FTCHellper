# Privacy and data handling

This milestone accepts MP4 video files up to 500 MB and stores them on the local filesystem under `backend/local-videos/`. It does not implement user accounts, access controls, or private object storage. Keep the services bound to `127.0.0.1`. Do not expose the API to a network or upload recordings containing students or minors until authenticated access, retention/deletion controls, and private storage are implemented and reviewed.

Uploaded content will not be used for model training by default. A future upload workflow must validate file type and size, avoid public URLs, clean temporary artifacts, and enforce tenant access on the server and in database policies.

Manual annotations are stored locally with timestamps, event type, optional robot label and note, source, and review status. They are user-entered observations; the application does not infer scoring or hardware causes from video.