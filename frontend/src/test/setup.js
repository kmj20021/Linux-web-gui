import '@testing-library/jest-dom/vitest'
import { expect } from 'vitest'
import * as axeMatchers from 'vitest-axe/matchers'

// 접근성 단언(toHaveNoViolations)을 모든 테스트에서 쓸 수 있게 한다.
expect.extend(axeMatchers)
