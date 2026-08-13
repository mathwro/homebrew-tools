class Nwcli < Formula
  desc "Network CLI Toolbox"
  homepage "https://github.com/mathwro/nwcli"
  license :cannot_represent

  on_macos do
    on_arm do
      url "https://github.com/mathwro/nwcli/releases/download/v0.1.0/nwcli_0.1.0_darwin_arm64.tar.gz"
      sha256 "ab7ebe6b73be1c733a771b9bef8bb9d6114f78430f5e970a4456a7b041802808"
    end
    on_intel do
      url "https://github.com/mathwro/nwcli/releases/download/v0.1.0/nwcli_0.1.0_darwin_amd64.tar.gz"
      sha256 "3aa26b30fd2a8c4819b36c219618211d36502e788b1c8643a763f629f0b9ea7b"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/nwcli/releases/download/v0.1.0/nwcli_0.1.0_linux_arm64.tar.gz"
      sha256 "c56d983b3c8c3c0b975ef9e9310c45388f0f098688f1fc0b29764d9956e550f5"
    end
    on_intel do
      url "https://github.com/mathwro/nwcli/releases/download/v0.1.0/nwcli_0.1.0_linux_amd64.tar.gz"
      sha256 "49d1915e5432a931d7a391b864a19a6518e3dd6d121c421e0ff9f1fe5fdbf2fc"
    end
  end

  def install
    bin.install "nwcli"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/nwcli --version")
  end
end
