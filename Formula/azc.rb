class Azc < Formula
  desc "Fast subscription context switcher for Azure CLI"
  homepage "https://github.com/mathwro/azc"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.3.0/azc_0.3.0_darwin_arm64.tar.gz"
      sha256 "69fcb48f38bc16be68b097e340f8072950b4496096f1d21258064596baa23377"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.3.0/azc_0.3.0_darwin_amd64.tar.gz"
      sha256 "5afdd8e070457bcffdb3eb2b916095bd2e1683aabff15dc117d2a4a7d66caa86"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.3.0/azc_0.3.0_linux_arm64.tar.gz"
      sha256 "ebdc32d9e033ea5abf336000b8ce6eab242cd743da9b587f748da4c27a9145d4"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.3.0/azc_0.3.0_linux_amd64.tar.gz"
      sha256 "b053bd08ddb523de417f623ce63e6139700f92d1526a288857086bcaecca19ae"
    end
  end

  def install
    bin.install "azc"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/azc --version")
  end
end
