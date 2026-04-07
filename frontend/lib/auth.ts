export const notionCookieNames = {
  accessToken: "notion_access_token",
  refreshToken: "notion_refresh_token",
  workspaceId: "notion_workspace_id",
  workspaceName: "notion_workspace_name",
  oauthState: "notion_oauth_state"
} as const;

export function notionOauthConfigured() {
  return Boolean(
    process.env.NOTION_OAUTH_CLIENT_ID &&
      process.env.NOTION_OAUTH_CLIENT_SECRET &&
      process.env.NOTION_OAUTH_REDIRECT_URI
  );
}

export function buildNotionAuthorizeUrl(state: string) {
  const clientId = process.env.NOTION_OAUTH_CLIENT_ID;
  const redirectUri = process.env.NOTION_OAUTH_REDIRECT_URI;

  if (!clientId || !redirectUri) {
    throw new Error("Notion OAuth is not configured.");
  }

  const params = new URLSearchParams({
    owner: "user",
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    state
  });

  return `https://api.notion.com/v1/oauth/authorize?${params.toString()}`;
}

export function oauthErrorRedirect(message: string) {
  const params = new URLSearchParams({
    error: message
  });

  return `/?${params.toString()}`;
}
