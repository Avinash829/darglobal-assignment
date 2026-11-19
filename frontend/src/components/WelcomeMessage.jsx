import { useState } from "react";
import { ArrowRightIcon, BuildingIcon, ChevronDownIcon, HomeIcon, SparkleIcon } from "./Icons";

// Every question here can be answered from the scraped data.
const QUESTION_GROUPS = [
  {
    title: "DarGlobal developments",
    icon: BuildingIcon,
    questions: [
      "Which DarGlobal projects are in Dubai?",
      "Tell me about Trump Tower Jeddah",
    ],
    moreQuestions: [
      "Which DarGlobal projects have golf communities?",
      "What branded residences does DarGlobal have with Lamborghini or Pagani?",
      "When will Trump International Hotel & Tower Dubai be completed?",
    ],
  },
  {
    title: "Wasalt listings",
    icon: HomeIcon,
    questions: [
      "Show me 3 bedroom apartments for rent on Wasalt",
      "How many villas are for sale on Wasalt?",
    ],
    moreQuestions: [
      "Which areas in Jeddah have villas for sale on Wasalt?",
      "Are there chalets for daily rental on Wasalt?",
      "Show me land for sale over 500 sqm on Wasalt",
    ],
  },
];

export default function WelcomeMessage({ onSelect, isDisabled }) {
  const [showMore, setShowMore] = useState(false);

  return (
    <section className="welcome">
      <div className="welcome__intro">
        <span className="avatar avatar--large"><SparkleIcon size={22} /></span>
        <div>
          <h2>Welcome to Property Assistant</h2>
          <p>
            Ask about DarGlobal&apos;s luxury developments across the UAE, Saudi Arabia, Qatar,
            Oman, Spain and the UK, or explore Wasalt property listings in Saudi Arabia.
          </p>
        </div>
      </div>

      <div className="welcome__groups">
        {QUESTION_GROUPS.map(({ title, icon: GroupIcon, questions, moreQuestions }) => (
          <div key={title} className="question-group">
            <h3><GroupIcon size={16} /> {title}</h3>
            {[...questions, ...(showMore ? moreQuestions : [])].map((question) => (
              <button key={question} className="question-option" disabled={isDisabled}
                      onClick={() => onSelect(question)}>
                <span>{question}</span>
                <ArrowRightIcon size={16} />
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="welcome__footer">
        {!showMore && (
          <button className="text-button" onClick={() => setShowMore(true)}>
            More options <ChevronDownIcon size={16} />
          </button>
        )}
        <span>Or type your own question below.</span>
      </div>
    </section>
  );
}
