import { localizeTutorial } from './localization';
import { createTutorialLauncher, TutorialLaunchOptions } from '@boardgamers/protocol/tutorial';
import launchGame, { destroyViewer } from './launch';
import { mountTutorial } from './tutorial/mount';

const tutorial = createTutorialLauncher(localizeTutorial(mountTutorial));
export function launch(selector: string) {
    tutorial.destroy();
    return launchGame(selector);
}
export function launchTutorial(selector: string, options: TutorialLaunchOptions) {
    destroyViewer();
    return tutorial.launch(selector, options);
}

if (typeof window !== 'undefined') {
    (window as any).powergrid = { launch, launchTutorial };
}

export default launch;
