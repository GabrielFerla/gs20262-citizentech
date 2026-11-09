// Preparação dos testes (Jest): armazenamento e área segura de mentira.
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);
jest.mock('react-native-safe-area-context', () => require('react-native-safe-area-context/jest/mock').default);

// O TanStack Query avisa a tela fora do React; nos testes, cada aviso vai dentro de act()
// (sem isso, o React reclama de "update not wrapped in act").
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { act } = require('react') as typeof import('react');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { notifyManager } = require('@tanstack/react-query') as typeof import('@tanstack/react-query');
notifyManager.setNotifyFunction((avisar) => {
  act(avisar);
});
