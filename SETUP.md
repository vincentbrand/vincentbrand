# Setup

## 1. Turn on private contributions

On github.com, open your profile, click "Contribution settings" above the
contribution graph and enable "Private contributions". Without this GitHub does
not report private activity to anyone, including the build.

## 2. Create a token

1. Go to https://github.com/settings/tokens and choose "Generate new token (classic)".
2. Tick only the `read:user` scope. This token cannot read any code.
3. Copy the token.

## 3. Store it as a secret

In the `vincentbrand/vincentbrand` repo: Settings > Secrets and variables >
Actions > New repository secret. Name it `PROFILE_TOKEN` and paste the token.

## 4. Install the files

From this folder, with your profile repo cloned next to it:

    cp -R build.py README.md .github ../vincentbrand/
    cd ../vincentbrand
    git rm -q ascii.txt img2ascii.py
    git add -A
    git commit -m "New neural profile card"
    git push

The push starts the build. The build log prints how many public commits and
private contributions it found, so you can check the token works.

## Preview locally

    python build.py --offline

## What the numbers mean

- Commits: public commits plus your private contribution count, summed over
  every year of your account. This is the same data as your profile graph.
- GitHub reports private activity as one combined number, so private pull
  requests, issues and reviews are included in it along with private commits.
- GitHub only counts commits on a default branch whose author email is linked
  to your account.
- Last 7 days and weekly average (past 52 weeks) use the same counting.
- Neurons firing in the brain: one per two commits in the last 7 days
  (minimum 4, maximum 26).
