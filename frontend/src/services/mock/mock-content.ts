import type { Grade, Word } from "../types";

// [word, syllables, definition, example, [3 wrong meanings], explanation]
type Row = [string, string, string, string, [string, string, string], string];

const RAW: Record<Grade, Row[]> = {
  K: [
    ["happy", "hap · py", "Feeling good and glad.", "I feel happy when I play with my dog.", ["Feeling sleepy", "Very cold", "Very loud"], "Happy means you feel good inside!"],
    ["big", "big", "Very large in size.", "The elephant is very big.", ["Very small", "Very fast", "Very wet"], "Big things take up lots of space."],
    ["jump", "jump", "To push off the ground with your feet.", "The frog can jump high.", ["To sit still", "To eat food", "To sing a song"], "When you jump, your feet leave the ground."],
    ["soft", "soft", "Nice and gentle to touch, not hard.", "My pillow is soft.", ["Hard like a rock", "Very hot", "Bright and shiny"], "Soft things feel squishy and gentle."],
    ["share", "share", "To let others use or have some of what you have.", "I share my crayons with my friend.", ["To hide something", "To break something", "To run away"], "Sharing means giving others a turn too."],
  ],
  "1": [
    ["brave", "brave", "Ready to face something scary.", "The brave kitten climbed down the tree.", ["Very tired", "Very hungry", "Very quiet"], "Brave people try even when they feel scared."],
    ["gentle", "gen · tle", "Kind and careful, not rough.", "Be gentle when you pet the bunny.", ["Loud and fast", "Mean and rough", "Sleepy and slow"], "Gentle means soft and careful."],
    ["giant", "gi · ant", "Something huge.", "A giant tree stood in the park.", ["Something tiny", "Something round", "Something sticky"], "Giant things are really, really big."],
    ["quick", "quick", "Fast.", "The rabbit made a quick hop.", ["Slow", "Heavy", "Wet"], "Quick means it happens fast."],
    ["shout", "shout", "To speak very loudly.", "We shout 'hooray' at the game.", ["To whisper", "To sleep", "To draw"], "A shout is a loud voice."],
  ],
  "2": [
    ["curious", "cu · ri · ous", "Wanting to know or learn about something.", "The curious girl asked many questions.", ["Feeling angry", "Very sleepy", "Not interested"], "Curious people love to find things out."],
    ["enormous", "e · nor · mous", "Extremely big.", "The whale was enormous.", ["Very tiny", "Very shiny", "Very fast"], "Enormous is even bigger than big!"],
    ["fragile", "frag · ile", "Easy to break.", "The glass vase is fragile.", ["Very strong", "Very heavy", "Very loud"], "Fragile things need careful handling."],
    ["journey", "jour · ney", "A trip from one place to another.", "Our journey to grandma's took all day.", ["A kind of food", "A loud noise", "A small bug"], "A journey is travel from here to there."],
    ["wander", "wan · der", "To walk around without a plan.", "We like to wander in the woods.", ["To stand still", "To build a house", "To shout loudly"], "Wandering means exploring with no fixed path."],
  ],
  "3": [
    ["observe", "ob · serve", "To watch carefully.", "We observe the birds at the feeder.", ["To ignore", "To throw away", "To forget"], "Observing means looking closely."],
    ["predict", "pre · dict", "To say what you think will happen.", "I predict it will rain today.", ["To remember the past", "To clean up", "To paint a picture"], "Predicting is a smart guess about the future."],
    ["ancient", "an · cient", "Very, very old.", "We saw ancient pyramids in the book.", ["Brand new", "Very colorful", "Very small"], "Ancient things are from long ago."],
    ["cautious", "cau · tious", "Careful to avoid danger.", "Be cautious when crossing the street.", ["Careless", "Silly", "Sleepy"], "Cautious people think before they act."],
    ["delighted", "de · light · ed", "Very pleased and happy.", "She was delighted with her gift.", ["Very upset", "Very bored", "Very confused"], "Delighted is a big, happy feeling."],
  ],
  "4": [
    ["abundant", "a · bun · dant", "More than enough; plenty.", "Apples were abundant at the orchard.", ["Very rare", "Broken", "Hidden"], "Abundant means there's lots of it."],
    ["reluctant", "re · luc · tant", "Not wanting to do something.", "He was reluctant to jump in the cold pool.", ["Very eager", "Very proud", "Very fast"], "Reluctant means you hold back."],
    ["vivid", "viv · id", "Bright and clear.", "The painting had vivid colors.", ["Dull and faded", "Very quiet", "Very heavy"], "Vivid things are strong and lively."],
    ["persuade", "per · suade", "To get someone to agree by giving reasons.", "She tried to persuade her dad to get a puppy.", ["To forget", "To hide from", "To copy"], "Persuading uses good reasons to change minds."],
    ["habitat", "hab · i · tat", "The natural home of an animal or plant.", "The desert is the camel's habitat.", ["A kind of hat", "A daily routine", "A loud song"], "A habitat is where something naturally lives."],
  ],
  "5": [
    ["consequence", "con · se · quence", "A result of an action.", "A consequence of staying up late is feeling tired.", ["A reward for nothing", "A type of map", "A kind of plant"], "Consequences follow from what we do."],
    ["diligent", "dil · i · gent", "Hard-working and careful.", "The diligent student checked every answer.", ["Lazy", "Forgetful", "Noisy"], "Diligent people put in steady effort."],
    ["evidence", "ev · i · dence", "Facts or signs that show something is true.", "Muddy paw prints were evidence the dog came in.", ["A wild guess", "A secret wish", "A kind of tool"], "Evidence helps prove what happened."],
    ["hesitate", "hes · i · tate", "To pause before doing something.", "She did not hesitate to help.", ["To rush ahead", "To shout", "To finish quickly"], "Hesitating is a small pause of doubt."],
    ["resourceful", "re · source · ful", "Good at finding clever ways to solve problems.", "The resourceful camper made a tent from a tarp.", ["Wasteful", "Helpless", "Unkind"], "Resourceful people make the most of what they have."],
  ],
  "6": [
    ["analyze", "an · a · lyze", "To study something closely to understand it.", "We analyze the data from our experiment.", ["To guess quickly", "To throw away", "To decorate"], "Analyzing means breaking something down to understand it."],
    ["benevolent", "be · nev · o · lent", "Kind and wanting to help others.", "The benevolent queen fed the hungry.", ["Cruel", "Lazy", "Shy"], "Benevolent people wish others well."],
    ["contradict", "con · tra · dict", "To say the opposite of something.", "His actions contradict his words.", ["To agree completely", "To repeat exactly", "To forget"], "Contradicting means going against what was said."],
    ["elaborate", "e · lab · o · rate", "Detailed and complex.", "She made an elaborate sandcastle with towers.", ["Very plain", "Very quick", "Broken"], "Elaborate things have many careful details."],
    ["perspective", "per · spec · tive", "A way of seeing or thinking about something.", "Try to see it from your friend's perspective.", ["A kind of glasses", "A loud argument", "A math rule"], "A perspective is a point of view."],
  ],
  "7": [
    ["ambiguous", "am · big · u · ous", "Having more than one possible meaning.", "The ambiguous sign confused drivers.", ["Perfectly clear", "Very old", "Very loud"], "Ambiguous things can be understood in different ways."],
    ["candid", "can · did", "Honest and direct.", "She gave a candid answer about her mistake.", ["Secretive", "Rude", "Sleepy"], "Candid means telling it like it is."],
    ["meticulous", "me · tic · u · lous", "Showing great attention to detail.", "He was meticulous about his model trains.", ["Careless", "Hurried", "Bored"], "Meticulous people sweat the small stuff."],
    ["resilient", "re · sil · ient", "Able to recover quickly from difficulty.", "The resilient team bounced back after losing.", ["Easily broken", "Always angry", "Very slow"], "Resilient people bounce back."],
    ["inevitable", "in · ev · i · ta · ble", "Certain to happen.", "With dark clouds, rain seemed inevitable.", ["Impossible", "Unlikely", "Forgotten"], "Inevitable means it can't be avoided."],
  ],
  "8": [
    ["advocate", "ad · vo · cate", "To publicly support a cause.", "She will advocate for a new park.", ["To oppose quietly", "To forget about", "To laugh at"], "Advocating means speaking up for something."],
    ["coherent", "co · her · ent", "Clear and logical.", "His essay was coherent and easy to follow.", ["Confusing", "Very short", "Very loud"], "Coherent ideas fit together sensibly."],
    ["empathy", "em · pa · thy", "Understanding and sharing someone else's feelings.", "She showed empathy for her sad friend.", ["Jealousy", "Boredom", "Anger"], "Empathy is feeling with someone."],
    ["scrutinize", "scru · ti · nize", "To examine very carefully.", "The judge will scrutinize the evidence.", ["To glance at", "To ignore", "To destroy"], "Scrutinizing is looking with extra care."],
    ["tenacious", "te · na · cious", "Holding firmly; not giving up.", "The tenacious climber reached the top.", ["Quitting easily", "Very gentle", "Very noisy"], "Tenacious people keep going."],
  ],
  "9": [
    ["ephemeral", "e · phem · er · al", "Lasting a very short time.", "The rainbow was ephemeral.", ["Lasting forever", "Very heavy", "Very expensive"], "Ephemeral things fade quickly."],
    ["pragmatic", "prag · mat · ic", "Dealing with things in a practical way.", "She took a pragmatic approach to the budget.", ["Dreamy and unrealistic", "Rude", "Sad"], "Pragmatic means focused on what works."],
    ["ubiquitous", "u · biq · ui · tous", "Found everywhere.", "Smartphones are ubiquitous today.", ["Very rare", "Very old", "Invisible"], "Ubiquitous things seem to be everywhere."],
    ["benign", "be · nign", "Gentle and harmless.", "The doctor said the bump was benign.", ["Dangerous", "Loud", "Expensive"], "Benign means not harmful."],
    ["juxtapose", "jux · ta · pose", "To place side by side to compare.", "The artist juxtaposed old and new photos.", ["To hide away", "To throw out", "To melt down"], "Juxtaposing shows contrast by placing things together."],
  ],
  "10": [
    ["alleviate", "al · le · vi · ate", "To make something less severe.", "Medicine can alleviate pain.", ["To make worse", "To cause", "To ignore"], "Alleviating makes a problem lighter."],
    ["dichotomy", "di · chot · o · my", "A division into two opposite parts.", "There's a dichotomy between work and play.", ["A perfect match", "A type of animal", "A long speech"], "A dichotomy splits into two contrasting sides."],
    ["eloquent", "el · o · quent", "Speaking or writing well and persuasively.", "Her eloquent speech moved the crowd.", ["Mumbling", "Rude", "Silent"], "Eloquent words are clear and powerful."],
    ["mitigate", "mit · i · gate", "To reduce the harm of something.", "Trees mitigate flooding.", ["To increase", "To celebrate", "To copy"], "Mitigating lessens damage."],
    ["paradox", "par · a · dox", "A statement that seems to contradict itself but may be true.", "'Less is more' is a paradox.", ["A simple fact", "A type of boat", "A math answer"], "Paradoxes seem impossible but hold truth."],
  ],
  "11": [
    ["acquiesce", "ac · qui · esce", "To accept something without protest.", "He acquiesced to the new rules.", ["To argue loudly", "To run away", "To invent"], "Acquiescing means going along quietly."],
    ["cogent", "co · gent", "Clear, logical, and convincing.", "She made a cogent argument.", ["Weak and confusing", "Very funny", "Very long"], "Cogent arguments are convincing."],
    ["esoteric", "es · o · ter · ic", "Understood by only a few people.", "The lecture covered esoteric topics.", ["Widely known", "Very simple", "Very loud"], "Esoteric knowledge belongs to a small group."],
    ["obfuscate", "ob · fus · cate", "To make something unclear on purpose.", "The report tried to obfuscate the facts.", ["To explain clearly", "To celebrate", "To repair"], "Obfuscating hides meaning."],
    ["sycophant", "syc · o · phant", "Someone who flatters to gain favor.", "The king was surrounded by sycophants.", ["An honest critic", "A brave soldier", "A shy student"], "Sycophants say nice things to get ahead."],
  ],
  "12": [
    ["anachronism", "a · nach · ro · nism", "Something out of its proper time.", "A phone in a medieval film is an anachronism.", ["A future prediction", "A kind of clock", "A historic battle"], "Anachronisms don't belong in their time period."],
    ["equivocate", "e · quiv · o · cate", "To use unclear language to avoid committing.", "The politician equivocated on taxes.", ["To speak plainly", "To shout", "To agree"], "Equivocating dodges a clear answer."],
    ["perfunctory", "per · func · to · ry", "Done with little care or effort.", "He gave a perfunctory wave.", ["Very thorough", "Very joyful", "Very angry"], "Perfunctory means just going through the motions."],
    ["quintessential", "quin · tes · sen · tial", "The most perfect example of something.", "She's the quintessential team player.", ["The worst example", "A rare mistake", "A small part"], "Quintessential means the ideal example."],
    ["vicarious", "vi · car · i · ous", "Experienced through someone else.", "He felt vicarious joy at her win.", ["Firsthand", "Painful", "Forgotten"], "Vicarious feelings come through others' experiences."],
  ],
};

function build(grade: Grade): Word[] {
  return RAW[grade].map(([word, syllables, definition, example, wrong, explanation], i) => {
    const id = `g${grade}-w${i + 1}`;
    const correct = { id: `${id}-o0`, text: definition };
    const others = wrong.map((t, j) => ({ id: `${id}-o${j + 1}`, text: t }));
    // Deterministic placement of the correct answer.
    const options = [...others];
    options.splice(i % 4, 0, correct);
    return {
      id, word, grade, definition, example, syllables, contentVersion: "1.0",
      question: { id: `${id}-q`, options, correctOptionId: correct.id, explanation },
    };
  });
}

export function getMockGradeWords(grade: Grade): Word[] {
  return build(grade);
}
