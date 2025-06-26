# How to Push Your Project to Another GitHub Account

Follow these steps to upload your code to a different GitHub account:

---

## Quick Steps for a Different GitHub Account

1. **Remove any old remote:**
   ```bash
   git remote remove origin
   ```

2. **Create a new repository** on your new GitHub account ([github.com/new](https://github.com/new)), without a README.

3. **Add your new remote:**  
   Replace `YOUR_NEW_USERNAME` and `YOUR_NEW_REPO` below.
   ```bash
   git remote add origin https://github.com/YOUR_NEW_USERNAME/YOUR_NEW_REPO.git
   ```

4. **Push your code:**
   ```bash
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git push -u origin main
   ```

5. **Done!**  
   Your code is now on your new GitHub account.

---

**Tip:**  
If asked for credentials, use your new GitHub username and a [personal access token](https://github.com/settings/tokens).
