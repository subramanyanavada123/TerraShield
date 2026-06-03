# Contributing to TerraShield

Thank you for your interest in contributing to TerraShield! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites
- Node.js 16+
- npm or yarn
- Git
- GitHub account

### Development Setup

```bash
# Clone the repository
git clone https://github.com/subramanyanavada123/TerraShield.git
cd TerraShield

# Install dependencies
npm install

# Start development server
npm run dev
```

## Workflow

### 1. Create a Feature Branch

Always create a new branch for your work. Never commit directly to `master`.

```bash
# Update master first
git checkout master
git pull origin master

# Create a descriptive branch name
git checkout -b feature/description-of-feature
# or
git checkout -b fix/description-of-fix
git checkout -b docs/description-of-docs
```

### 2. Make Changes

- Write clear, maintainable code
- Follow the existing code style (ES6+, React conventions)
- Add comments for complex logic
- Keep components focused and reusable

### 3. Test Your Changes

```bash
# Run the development server
npm run dev

# Test the complete demo sequence
# 1. Wait for page load (typewriter effects complete)
# 2. Click attack button
# 3. Verify all timings and effects work
# 4. Click reset button
# 5. Verify state fully restores
```

### 4. Commit with Clear Messages

Use conventional commit format:

```bash
git add .
git commit -m "feat: add new feature description"
```

**Commit types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code formatting (no logic changes)
- `refactor:` - Code reorganization (no logic/feature changes)
- `perf:` - Performance improvements
- `test:` - Test additions/updates
- `chore:` - Build/dependencies/tooling

**Examples:**
```bash
git commit -m "feat: add keyboard shortcuts for demo control"
git commit -m "fix: correct animation timing in provenance panel"
git commit -m "docs: update README with new features"
git commit -m "perf: optimize correlation calculation loop"
```

### 5. Push to GitHub

```bash
git push origin feature/your-feature-name
```

### 6. Create a Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select your branch
4. Fill in title and description
5. Request review if applicable

### 7. Address Review Feedback

If reviewers request changes:
```bash
# Make requested changes
git add .
git commit -m "review: address feedback on feature"
git push origin feature/your-feature-name
```

## Code Style Guidelines

### React Components

```javascript
// Use functional components with hooks
function MyComponent({ prop1, prop2 }) {
  const [state, setState] = useState(initialValue)

  useEffect(() => {
    // Side effects
    return () => {
      // Cleanup
    }
  }, [dependencies])

  return (
    <div>
      {/* JSX content */}
    </div>
  )
}
```

### Styling

- Use inline styles via `style` prop for component-specific styling
- Use CSS classes for animations and pseudo-elements
- Follow existing color palette (#ef4444 red, #f59e0b amber, #22c55e green)
- Maintain responsive design

### Comments

```javascript
// Use comments for "why", not "what"
// Good:
// Lerp the correlation smoothly over 80ms to prevent jarring changes
const lerpFactor = 0.12

// Avoid:
// Set lerpFactor to 0.12
const lerpFactor = 0.12
```

## Testing Checklist

Before submitting a PR, verify:

- [ ] No console errors or warnings
- [ ] All existing features still work
- [ ] New feature works as intended
- [ ] Animations are smooth (60 FPS)
- [ ] Responsive at different viewport sizes
- [ ] Reset button fully restores state
- [ ] Audio works and mute toggle functions
- [ ] No unwanted side effects on other components

## Documentation

### README.md
Update if:
- Adding new features
- Changing installation steps
- Modifying project structure
- Adding dependencies

### Inline Comments
Add comments for:
- Complex algorithms
- Non-obvious design decisions
- Performance optimizations
- Workarounds for browser quirks

### POLISH_IMPLEMENTATION.md
Update for v3.0+ visual/UX enhancements with detailed implementation notes

## Common Tasks

### Adding a New Feature

1. Create branch: `git checkout -b feature/feature-name`
2. Implement feature in appropriate component
3. Update README if user-facing
4. Test thoroughly
5. Commit with clear message
6. Push and create PR

### Fixing a Bug

1. Create branch: `git checkout -b fix/bug-description`
2. Reproduce bug locally
3. Implement fix
4. Verify fix doesn't break other features
5. Commit: `git commit -m "fix: description of fix"`
6. Push and create PR

### Updating Documentation

1. Create branch: `git checkout -b docs/doc-name`
2. Update relevant .md files
3. Commit: `git commit -m "docs: update documentation"`
4. Push and create PR

## Issues

### Reporting Issues

When reporting bugs, include:
- Browser and OS
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots if applicable

### Working on Issues

1. Comment on the issue to express interest
2. Wait for maintainer approval
3. Create a branch based on the issue number
4. Make your changes
5. Reference the issue in your PR

## Branch Naming Convention

- `feature/short-description` - New features
- `fix/short-description` - Bug fixes
- `docs/short-description` - Documentation
- `refactor/short-description` - Code refactoring
- `perf/short-description` - Performance improvements

## Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Demo sequence works
- [ ] Reset button restores state
- [ ] No console errors
- [ ] Responsive design intact

## Related Issues
Fixes #(issue number)
```

## Questions or Need Help?

- Check existing issues for answers
- Review code comments and documentation
- Ask in GitHub discussions or issues

## Code of Conduct

- Be respectful and professional
- Welcome diverse perspectives
- Focus on constructive feedback
- Help other contributors

## Recognition

Contributors will be recognized in:
- README acknowledgments section
- GitHub contributors page
- Release notes for significant contributions

---

Thank you for contributing to TerraShield! 🚀
