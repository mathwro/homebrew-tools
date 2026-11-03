class Azc < Formula
  desc "Fast subscription context switcher for Azure CLI"
  homepage "https://github.com/mathwro/azc"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.5.0/azc_0.5.0_darwin_arm64.tar.gz"
      sha256 "a0dd6d4f1a70e2bf4945089a961b3518724272f7d665dbda989acb8380b22a8b"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.5.0/azc_0.5.0_darwin_amd64.tar.gz"
      sha256 "565b6b872ab9fb2d1d6009ad97042064483411801cf08a014432deaac08e08b2"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.5.0/azc_0.5.0_linux_arm64.tar.gz"
      sha256 "792bf48076f8846901041bd39fc1af191adaa1030d6b37fbae17ee51705885ad"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.5.0/azc_0.5.0_linux_amd64.tar.gz"
      sha256 "215dcefd21ce9c5e796d9620f1d2ccf2a467a871b0d595b98e95bf0221237ff9"
    end
  end

  def install
    bin.install "azc"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/azc --version")
  end
end
