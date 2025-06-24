import {ActionFunction} from '@remix-run/node';

import {authenticate} from '../shopify.server';
import {formatComplianceBlocks, sendSlackMessage} from "../utils/slack.server";

export const action: ActionFunction = async ({request}) => {
  const { payload, topic, shop } = await authenticate.webhook(request);

  await sendSlackMessage(
        topic,
        formatComplianceBlocks(topic, { ...payload, shop_domain: shop })
      );
  switch (topic) {
    case 'APP_UNINSTALLED':
      break;
    case 'CUSTOMERS_DATA_REQUEST':
      break;
    case 'CUSTOMERS_REDACT':
      break;
    case 'SHOP_REDACT':
      break;
    case 'SCOPES_UPDATE':
      break;
    default:
      throw new Response('Unhandled webhook topic', {status: 404});
  }

  throw new Response();
};
